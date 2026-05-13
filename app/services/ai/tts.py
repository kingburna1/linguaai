import asyncio
import tempfile
import os
from typing import Optional

from app.core.config import settings
from app.storage.supabase_storage import upload_audio_file, delete_temp_file


class TTSService:
    """
    Uses two engines in order:
      1. Edge TTS (Microsoft) — free, fast, 400+ voices, many languages
                                No install needed beyond the pip package.
                                Used as PRIMARY engine.

      2. Coqui TTS            — free, local, very high quality
                                Slower, needs model download (~2GB).
                                Used as FALLBACK if Edge TTS fails.

    Edge TTS is preferred because:
      - Instant (cloud-based, no local model needed)
      - Supports almost every language on your platform
      - No GPU required
      - Much faster than Coqui for real-time conversation
    """
    EDGE_VOICES = {
        "fr": {"female": "fr-FR-DeniseNeural",    "male": "fr-FR-HenriNeural"},
        "es": {"female": "es-ES-ElviraNeural",    "male": "es-ES-AlvaroNeural"},
        "de": {"female": "de-DE-KatjaNeural",     "male": "de-DE-ConradNeural"},
        "it": {"female": "it-IT-ElsaNeural",      "male": "it-IT-DiegoNeural"},
        "pt": {"female": "pt-BR-FranciscaNeural", "male": "pt-BR-AntonioNeural"},
        "zh": {"female": "zh-CN-XiaoxiaoNeural",  "male": "zh-CN-YunxiNeural"},
        "ja": {"female": "ja-JP-NanamiNeural",    "male": "ja-JP-KeitaNeural"},
        "ko": {"female": "ko-KR-SunHiNeural",     "male": "ko-KR-InJoonNeural"},
        "ar": {"female": "ar-SA-ZariyahNeural",   "male": "ar-SA-HamedNeural"},
        "hi": {"female": "hi-IN-SwaraNeural",     "male": "hi-IN-MadhurNeural"},
        "sw": {"female": "sw-KE-ZuriNeural",      "male": "sw-KE-RafikiNeural"},
        "yo": {"female": "yo-NG-IsiolaNeural",    "male": "yo-NG-EzinneNeural"},
        "en": {"female": "en-US-JennyNeural",     "male": "en-US-GuyNeural"},
    }

    DEFAULT_VOICE = {"female": "en-US-JennyNeural", "male": "en-US-GuyNeural"}

    async def synthesize(
        self,
        text:          str,
        language_code: str = "en",
        voice_gender:  str = "female",
        upload:        bool = True,
    ) -> str:
        try:
            return await self._synthesize_edge(
                text, language_code, voice_gender, upload
            )
        except Exception as e:
            print(f"[TTS] Edge TTS failed: {e} — trying Coqui fallback")
            try:
                return await self._synthesize_coqui(text, language_code, upload)
            except Exception as e2:
                print(f"[TTS] Coqui also failed: {e2}")
                raise RuntimeError(
                    f"All TTS engines failed. Edge: {e} | Coqui: {e2}"
                )

    async def _synthesize_edge(
        self,
        text:          str,
        language_code: str,
        voice_gender:  str,
        upload:        bool,
    ) -> str:
      
        import edge_tts

      
        voices      = self.EDGE_VOICES.get(language_code, self.DEFAULT_VOICE)
        voice_name  = voices.get(voice_gender, voices["female"])

        
        tmp_path = tempfile.mktemp(suffix=".mp3")
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice_name)

            
            await communicate.save(tmp_path)

            if upload:
                url = await upload_audio_file(
                    tmp_path,
                    folder       = "ai_responses",
                    content_type = "audio/mpeg",
                )
                return url
            else:
                return tmp_path

        finally:
            if upload:
                delete_temp_file(tmp_path)

    async def _synthesize_coqui(
        self,
        text:          str,
        language_code: str,
        upload:        bool,
    ) -> str:
        from TTS.api import TTS as CoquiTTS

        tmp_path = tempfile.mktemp(suffix=".wav")
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._run_coqui(text, language_code, tmp_path)
            )

            if upload:
                url = await upload_audio_file(
                    tmp_path,
                    folder       = "ai_responses",
                    content_type = "audio/wav",
                )
                return url
            else:
                return tmp_path

        finally:
            if upload:
                delete_temp_file(tmp_path)

    def _run_coqui(self, text: str, language_code: str, output_path: str) -> None:
        """Synchronous Coqui TTS call — runs inside thread pool."""
        from TTS.api import TTS as CoquiTTS
        tts = CoquiTTS(model_name=settings.TTS_MODEL, progress_bar=False)
        tts.tts_to_file(
            text         = text,
            file_path    = output_path,
            language     = language_code,
        )

    def get_voice_for_user(
        self,
        language_code:  str,
        preferred_voice: str = "female",
    ) -> str:
       
        voices = self.EDGE_VOICES.get(language_code, self.DEFAULT_VOICE)
        return voices.get(preferred_voice, voices["female"])


tts_service = TTSService()