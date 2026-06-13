import logging
import time
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class Transcriber:
    """Wrapper around faster-whisper for CPU-based ASR."""

    def __init__(self, model_size: str = "base"):
        logger.info("Loading faster-whisper model '%s' on CPU...", model_size)
        start = time.time()
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        elapsed = time.time() - start
        logger.info("Model loaded in %.1fs", elapsed)

    def transcribe(self, audio_path: str, language: str = "zh") -> dict:
        """
        Transcribe audio file to text with timestamps.

        Returns:
        {
            "language": "zh",
            "segments": [
                {"start": 0.0, "end": 5.2, "text": "..."},
                ...
            ],
            "full_text": "..."
        }
        """
        logger.info("Starting transcription: %s", audio_path)
        start = time.time()

        segments_gen, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        segments = []
        for seg in segments_gen:
            segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            })

        full_text = " ".join(s["text"] for s in segments)
        elapsed = time.time() - start
        logger.info(
            "Transcription complete in %.1fs, %d segments, detected language: %s",
            elapsed, len(segments), info.language,
        )

        return {
            "language": info.language,
            "segments": segments,
            "full_text": full_text,
        }
