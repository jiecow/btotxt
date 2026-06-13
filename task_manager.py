import json
import os
import uuid
import threading
import logging
from datetime import datetime

from . import config
from .downloader import download_audio, convert_to_wav, extract_title
from .transcriber import Transcriber
from .llm_handler import LLMHandler

logger = logging.getLogger(__name__)

_current_task = None
_current_task_lock = threading.Lock()


def _get_task_path(task_id: str) -> str:
    return os.path.join(config.TRANSCRIPTS_DIR, f"{task_id}.json")


def _save_task(task: dict):
    path = _get_task_path(task["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False, indent=2)


def _load_task(task_id: str) -> dict:
    path = _get_task_path(task_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_task(task_id: str) -> dict | None:
    """Get task by ID. Returns None if not found."""
    path = _get_task_path(task_id)
    if not os.path.exists(path):
        return None
    return _load_task(task_id)


def list_tasks() -> list:
    """List all recent task IDs and statuses."""
    tasks = []
    if not os.path.exists(config.TRANSCRIPTS_DIR):
        return tasks
    for fname in sorted(os.listdir(config.TRANSCRIPTS_DIR), reverse=True):
        if fname.endswith(".json"):
            path = os.path.join(config.TRANSCRIPTS_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tasks.append({
                    "id": data["id"],
                    "status": data["status"],
                    "title": data.get("title", ""),
                    "created_at": data.get("created_at", ""),
                })
            except (json.JSONDecodeError, OSError):
                continue
    return tasks


def create_task(url: str) -> str:
    """Create a new task and start background processing."""
    global _current_task

    task_id = uuid.uuid4().hex[:12]
    task = {
        "id": task_id,
        "url": url,
        "status": "queued",
        "progress": 0,
        "title": "",
        "message": "等待处理...",
        "full_text": "",
        "segments": [],
        "polished_text": "",
        "notes": "",
        "error": "",
        "created_at": datetime.now().isoformat(),
    }
    _save_task(task)

    with _current_task_lock:
        if _current_task is not None:
            return task_id
        _current_task = task_id

    _start_processing(task_id)
    return task_id


def _start_processing(task_id: str):
    thread = threading.Thread(target=_run_pipeline, args=(task_id,), daemon=True)
    thread.start()


def _update_task(task_id: str, **kwargs):
    task = _load_task(task_id)
    task.update(**kwargs)
    _save_task(task)


def _run_pipeline(task_id: str):
    global _current_task

    audio_path = None
    wav_path = None

    try:
        task = _load_task(task_id)
        url = task["url"]

        # === Step 1: Download ===
        _update_task(task_id, status="downloading", progress=10, message="下载音频中...")
        logger.info("[%s] Downloading audio...", task_id)
        audio_path = download_audio(url, config.DOWNLOADS_DIR)
        title = extract_title(url)
        _update_task(task_id, progress=30, message="音频下载完成", title=title)

        # === Step 2: Convert ===
        _update_task(task_id, status="converting", progress=35, message="转换音频格式...")
        logger.info("[%s] Converting to WAV...", task_id)
        wav_path = convert_to_wav(audio_path, config.DOWNLOADS_DIR)

        # === Step 3: Transcribe ===
        _update_task(task_id, status="transcribing", progress=40, message="语音识别中...")
        logger.info("[%s] Transcribing...", task_id)
        transcriber = Transcriber(model_size=config.WHISPER_MODEL_SIZE)
        result = transcriber.transcribe(wav_path, language="zh")
        _update_task(
            task_id,
            progress=70,
            message=f"转写完成（{len(result['segments'])} 段）",
            segments=result["segments"],
            full_text=result["full_text"],
        )

        # === Step 4: LLM Polish ===
        _update_task(task_id, status="polishing", progress=75, message="AI 整理文本中...")
        logger.info("[%s] Polishing transcript...", task_id)
        llm = LLMHandler(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            model=config.DEEPSEEK_MODEL,
        )
        polished = llm.polish_transcript(result["full_text"])
        _update_task(task_id, progress=85, message="AI 整理完成")

        # === Step 5: LLM Notes ===
        _update_task(task_id, status="summarizing", progress=88, message="生成笔记摘要中...")
        logger.info("[%s] Generating notes...", task_id)
        notes = llm.generate_notes(polished)
        _update_task(
            task_id,
            status="done",
            progress=100,
            message="完成！",
            polished_text=polished,
            notes=notes,
        )
        logger.info("[%s] Pipeline complete!", task_id)

    except Exception as e:
        logger.exception("[%s] Pipeline failed", task_id)
        _update_task(task_id, status="error", message=str(e), error=str(e))

    finally:
        for p in [audio_path, wav_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                    logger.info("Cleaned up: %s", p)
                except OSError:
                    pass
        with _current_task_lock:
            _current_task = None
