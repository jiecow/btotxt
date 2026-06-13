import os
import subprocess
import re
import logging

logger = logging.getLogger(__name__)

BILIBILI_URL_PATTERN = re.compile(r"(https?://)?(www\.)?(b23\.tv|bilibili\.com)/")


def is_bilibili_url(url: str) -> bool:
    return bool(BILIBILI_URL_PATTERN.match(url))


def download_audio(url: str, output_dir: str) -> str:
    """
    Download audio from a Bilibili URL using yt-dlp.
    Returns path to the downloaded audio file (mp3).
    Raises RuntimeError on failure.
    """
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),
        "--no-playlist",
        "--print", "filename",
        url,
    ]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")
    lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
    if not lines:
        raise RuntimeError("yt-dlp produced no output")
    audio_path = lines[-1]
    if not os.path.exists(audio_path):
        raise RuntimeError(f"Downloaded file not found: {audio_path}")
    logger.info("Downloaded audio: %s", audio_path)
    return audio_path


def extract_title(url: str) -> str:
    """Extract video title using yt-dlp --print title."""
    cmd = ["yt-dlp", "--print", "title", "--no-playlist", url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        return result.stdout.strip()
    return "Unknown Title"


def convert_to_wav(mp3_path: str, output_dir: str) -> str:
    """
    Convert mp3 to 16kHz mono WAV for whisper input.
    Returns path to the WAV file.
    """
    base = os.path.splitext(os.path.basename(mp3_path))[0]
    wav_path = os.path.join(output_dir, f"{base}.wav")
    cmd = [
        "ffmpeg", "-y",
        "-i", mp3_path,
        "-ar", "16000",
        "-ac", "1",
        "-sample_fmt", "s16",
        wav_path,
    ]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed: {result.stderr.strip()}")
    logger.info("Converted to WAV: %s", wav_path)
    return wav_path
