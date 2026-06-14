import logging
from flask import (
    Flask, render_template, request, jsonify, redirect, url_for,
    Response,
)

from . import config
from .task_manager import create_task, create_import_task, get_task, list_tasks
from .subtitle_parser import detect_and_parse
from .llm_handler import NOTE_STYLES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def index():
    recent = list_tasks()[:10]
    return render_template("index.html", recent=recent, note_styles=NOTE_STYLES)


@app.route("/submit", methods=["POST"])
def submit():
    url = request.form.get("url", "").strip()
    note_style = request.form.get("note_style", "default")

    if not url:
        return render_template(
            "index.html", error="请输入 B 站视频链接",
            note_styles=NOTE_STYLES,
        )
    if "bilibili.com" not in url and "b23.tv" not in url:
        return render_template(
            "index.html", error="请输入有效的 B 站链接",
            note_styles=NOTE_STYLES,
        )
    if note_style not in NOTE_STYLES:
        note_style = "default"

    task_id = create_task(url, note_style=note_style)
    return redirect(url_for("processing", task_id=task_id))


@app.route("/processing/<task_id>")
def processing(task_id):
    task = get_task(task_id)
    if task is None:
        return redirect(url_for("index"))
    if task["status"] == "done":
        return redirect(url_for("result", task_id=task_id))
    if task["status"] == "error":
        return redirect(url_for("result", task_id=task_id))
    return render_template("processing.html", task_id=task_id)


@app.route("/status/<task_id>")
def status(task_id):
    task = get_task(task_id)
    if task is None:
        return jsonify({"status": "not_found"})
    return jsonify({
        "id": task["id"],
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"],
        "title": task.get("title", ""),
    })


@app.route("/result/<task_id>")
def result(task_id):
    task = get_task(task_id)
    if task is None:
        return redirect(url_for("index"))

    note_style_key = task.get("note_style", "default")
    note_style_label = NOTE_STYLES.get(note_style_key, {}).get("label", "")

    return render_template(
        "result.html",
        title=task.get("title", ""),
        status=task["status"],
        error=task.get("error", ""),
        segments=task.get("segments", []),
        full_text=task.get("full_text", ""),
        polished_text=task.get("polished_text", ""),
        notes=task.get("notes", ""),
        task_id=task_id,
        note_style_label=note_style_label,
    )


@app.route("/api/text/<task_id>")
def api_text(task_id):
    task = get_task(task_id)
    if task is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify({
        "full_text": task.get("full_text", ""),
        "polished_text": task.get("polished_text", ""),
        "notes": task.get("notes", ""),
    })


@app.route("/import", methods=["GET", "POST"])
def import_subtitle():
    if request.method == "GET":
        return render_template(
            "index.html", note_styles=NOTE_STYLES, show_import=True,
        )

    # POST: handle file upload
    file = request.files.get("subtitle_file")
    note_style = request.form.get("note_style", "default")

    if not file or file.filename == "":
        return render_template(
            "index.html",
            error="请选择一个字幕文件",
            note_styles=NOTE_STYLES,
            show_import=True,
        )

    # Validate file extension
    allowed = {".srt", ".vtt", ".txt"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in allowed:
        return render_template(
            "index.html",
            error=f"不支持的文件格式 .{ext}，请上传 .srt / .vtt / .txt 文件",
            note_styles=NOTE_STYLES,
            show_import=True,
        )

    if note_style not in NOTE_STYLES:
        note_style = "default"

    try:
        # Read and decode the file content
        raw = file.read()
        # Try UTF-8 first, fall back to common encodings
        content = None
        for enc in ["utf-8", "utf-16", "gbk", "gb2312", "latin-1"]:
            try:
                content = raw.decode(enc)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if content is None:
            return render_template(
                "index.html",
                error="无法识别文件编码，请使用 UTF-8 编码的字幕文件",
                note_styles=NOTE_STYLES,
                show_import=True,
            )

        # Parse the subtitle
        parsed = detect_and_parse(content, file.filename)
        if not parsed["segments"]:
            return render_template(
                "index.html",
                error="未能从文件中解析出字幕内容",
                note_styles=NOTE_STYLES,
                show_import=True,
            )

        # Create import task → goes straight to polish + notes
        task_id = create_import_task(
            full_text=parsed["full_text"],
            segments=parsed["segments"],
            note_style=note_style,
            title=file.filename,
        )
        return redirect(url_for("processing", task_id=task_id))

    except Exception as e:
        logger.exception("Import failed")
        return render_template(
            "index.html",
            error=f"导入失败: {e}",
            note_styles=NOTE_STYLES,
            show_import=True,
        )


@app.route("/export/<task_id>/<fmt>")
def export_task(task_id, fmt):
    """Export task results in various formats."""
    task = get_task(task_id)
    if task is None:
        return "Task not found", 404

    if fmt == "notes":
        content = task.get("notes", "")
        if not content:
            return "暂无笔记内容", 404
        return Response(
            content,
            mimetype="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=bili_notes_{task_id}.md"
                ),
            },
        )

    elif fmt == "transcript":
        content = task.get("polished_text", "") or task.get("full_text", "")
        if not content:
            return "暂无文本内容", 404
        return Response(
            content,
            mimetype="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=bili_transcript_{task_id}.txt"
                ),
            },
        )

    elif fmt == "srt":
        segments = task.get("segments", [])
        if not segments:
            return "暂无字幕段", 404
        # Build SRT content
        lines = []
        for i, seg in enumerate(segments, 1):
            start_s = _seconds_to_srt_time(seg["start"])
            end_s = _seconds_to_srt_time(seg["end"])
            lines.append(str(i))
            lines.append(f"{start_s} --> {end_s}")
            lines.append(seg["text"])
            lines.append("")  # blank line
        content = "\n".join(lines)
        return Response(
            content,
            mimetype="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=bili_subtitles_{task_id}.srt"
                ),
            },
        )

    else:
        return f"Unknown format: {fmt}", 400


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp format: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


if __name__ == "__main__":
    logger.info("Starting BiliSum on %s:%s", config.HOST, config.PORT)
    app.run(host=config.HOST, port=config.PORT, debug=False)
