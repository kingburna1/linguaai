import os
import asyncio
from typing import Optional

# Inject ffmpeg path directly — works without system PATH being set
os.environ["PATH"] = (
    r"C:\ffmpeg-8.1.1-essentials_build\ffmpeg-8.1.1-essentials_build\bin"
    + os.pathsep
    + os.environ.get("PATH", "")
)

import whisper

from app.core.config import settings
from app.storage.supabase_storage import save_temp_audio, delete_temp_file


class STTService:
    """
    Speech-to-Text service using OpenAI Whisper.
    Runs entirely on your local machine — completely free.

    Whisper model sizes and what they mean:
        tiny   → fastest, least accurate (~1 second)
        base   → good balance for dev testing
        small  → recommended — good accuracy, reasonable speed
        medium → better accuracy, slower (~4x small)
        large  → best accuracy, very slow, needs good GPU

    Set WHISPER_MODEL_SIZE in your .env — default is "small".
    The model downloads automatically on first use (~500MB for small).
    """

    def __init__(self):
        self._model = None   # lazy load — only downloads when first used

    def _load_model(self):
        """Loads the Whisper model into memory (once)."""
        if self._model is None:
            print(f"[STT] Loading Whisper model: {settings.WHISPER_MODEL_SIZE}")
            self._model = whisper.load_model(
                settings.WHISPER_MODEL_SIZE,
                device=settings.WHISPER_DEVICE,  # "cpu" or "cuda"
            )
            print("[STT] ✅ Whisper model loaded")
        return self._model

    async def transcribe_bytes(
        self,
        audio_bytes:   bytes,
        language_code: Optional[str] = None,
        audio_format:  str = ".webm",
    ) -> dict:
        """
        Transcribes raw audio bytes to text.
        Used when the audio comes directly from an upload.

        Args:
            audio_bytes   — raw bytes of the audio file
            language_code — ISO language code hint e.g. "fr", "yo", "sw"
                            Helps Whisper be more accurate. None = auto-detect.
            audio_format  — file extension for the temp file

        Returns dict:
            {
                "text":     "Bonjour, comment ça va?",
                "language": "fr",
                "duration": 3.2,   # seconds
                "words":    [...]   # word-level timestamps if available
            }
        """
        # Save bytes to a temp file — Whisper needs a file path
        tmp_path = save_temp_audio(audio_bytes, suffix=audio_format)
        try:
            return await self._transcribe_file(tmp_path, language_code)
        finally:
            delete_temp_file(tmp_path)

    async def transcribe_url(
        self,
        audio_url:     str,
        language_code: Optional[str] = None,
    ) -> dict:
        """
        Transcribes an audio file from its Supabase URL.
        Used when the audio was already uploaded and we have the URL.

        Args:
            audio_url     — Supabase public URL of the audio file
            language_code — ISO language code hint

        Returns same dict as transcribe_bytes.
        """
        from app.storage.supabase_storage import download_audio

        
        ext = os.path.splitext(audio_url.split("?")[0])[-1] or ".audio"

        audio_bytes = await download_audio(audio_url)
        return await self.transcribe_bytes(audio_bytes, language_code, ext)

    async def _transcribe_file(
        self,
        file_path:     str,
        language_code: Optional[str] = None,
    ) -> dict:
       
        model = self._load_model()

        options = {
            "task":          "transcribe",
            "word_timestamps": True,    
            "verbose":       False,
        }
        if language_code:
            options["language"] = language_code

        
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: model.transcribe(file_path, **options)
        )

        return {
            "text":     result.get("text", "").strip(),
            "language": result.get("language", language_code or "unknown"),
            "duration": self._get_duration(result),
            "words":    result.get("words", []),
        }

    def _get_duration(self, result: dict) -> float:
        """Extracts total audio duration from Whisper result segments."""
        segments = result.get("segments", [])
        if segments:
            return segments[-1].get("end", 0.0)
        return 0.0

    async def score_pronunciation(
        self,
        user_text:    str,
        expected_text: str,
    ) -> float:
       
        if not expected_text:
            return 100.0  

        user_words     = set(user_text.lower().split())
        expected_words = set(expected_text.lower().split())

        if not expected_words:
            return 100.0

        matches = len(user_words & expected_words)
        score   = (matches / len(expected_words)) * 100.0
        return round(min(score, 100.0), 2)



stt_service = STTService()