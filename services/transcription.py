from pathlib import Path
from typing import Optional


AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".webm", ".opus", ".mp4"}


class TranscriptionService:
    async def transcribe(self, audio_path: Path, openai_key: Optional[str]) -> str:
        if not openai_key:
            raise ValueError(
                "Chave OpenAI necessária para transcrição de áudio. "
                "Configure a chave em Configurações → ChatGPT (OpenAI)."
            )
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=openai_key)
        with open(audio_path, "rb") as fh:
            result = await client.audio.transcriptions.create(
                model="whisper-1",
                file=fh,
                response_format="text",
            )
        return result if isinstance(result, str) else result.text
