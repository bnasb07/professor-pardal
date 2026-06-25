import asyncio
import base64
from typing import List, Dict, Optional

PROVIDERS_META = {
    "anthropic": {
        "name": "Claude (Anthropic)",
        "models": ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5-20251001"],
        "default_model": "claude-sonnet-4-6",
        "supports_vision": True,
    },
    "openai": {
        "name": "ChatGPT (OpenAI)",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "default_model": "gpt-4o",
        "supports_vision": True,
    },
    "gemini": {
        "name": "Gemini (Google)",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "default_model": "gemini-2.0-flash",
        "supports_vision": True,
    },
}


class AIProviderService:
    def __init__(self):
        self._configs: Dict[str, Dict] = {}

    def update_provider(self, provider: str, api_key: str, model: Optional[str] = None):
        self._configs[provider] = {"api_key": api_key, "model": model}

    def get_providers_meta(self):
        result = {}
        for k, v in PROVIDERS_META.items():
            result[k] = {
                **v,
                "configured": k in self._configs and bool(self._configs[k].get("api_key")),
            }
        return result

    async def chat(
        self,
        provider: str,
        api_key: str,
        model: Optional[str],
        system: str,
        messages: List[Dict],
        images: List[str] = [],
    ) -> str:
        if provider == "anthropic":
            return await self._chat_anthropic(api_key, model, system, messages, images)
        elif provider == "openai":
            return await self._chat_openai(api_key, model, system, messages, images)
        elif provider == "gemini":
            return await self._chat_gemini(api_key, model, system, messages, images)
        else:
            raise ValueError(f"Provider desconhecido: {provider}")

    async def _chat_anthropic(
        self,
        api_key: str,
        model: Optional[str],
        system: str,
        messages: List[Dict],
        images: List[str],
    ) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)

        formatted = []
        for msg in messages[:-1]:
            formatted.append({"role": msg["role"], "content": msg["content"]})

        last = messages[-1]
        if images:
            content = [{"type": "text", "text": last["content"]}]
            for img in images:
                media_type = "image/png"
                data = img
                if img.startswith("data:"):
                    header, data = img.split(",", 1)
                    media_type = header.split(":")[1].split(";")[0]
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": data},
                })
            formatted.append({"role": "user", "content": content})
        else:
            formatted.append({"role": "user", "content": last["content"]})

        resp = await client.messages.create(
            model=model or "claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            messages=formatted,
        )
        return resp.content[0].text

    async def _chat_openai(
        self,
        api_key: str,
        model: Optional[str],
        system: str,
        messages: List[Dict],
        images: List[str],
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        formatted = [{"role": "system", "content": system}]

        for msg in messages[:-1]:
            formatted.append({"role": msg["role"], "content": msg["content"]})

        last = messages[-1]
        if images:
            content: List = [{"type": "text", "text": last["content"]}]
            for img in images:
                url = img if img.startswith("data:") else f"data:image/png;base64,{img}"
                content.append({"type": "image_url", "image_url": {"url": url}})
            formatted.append({"role": "user", "content": content})
        else:
            formatted.append({"role": "user", "content": last["content"]})

        resp = await client.chat.completions.create(
            model=model or "gpt-4o",
            messages=formatted,
            max_tokens=4096,
        )
        return resp.choices[0].message.content

    async def _chat_gemini(
        self,
        api_key: str,
        model: Optional[str],
        system: str,
        messages: List[Dict],
        images: List[str],
    ) -> str:
        import google.generativeai as genai
        import PIL.Image
        import io

        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(
            model_name=model or "gemini-2.0-flash",
            system_instruction=system,
        )

        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        chat = gemini_model.start_chat(history=history)

        last = messages[-1]
        parts: List = [last["content"]]

        for img in images:
            try:
                raw = img.split(",", 1)[1] if img.startswith("data:") else img
                pil_img = PIL.Image.open(io.BytesIO(base64.b64decode(raw)))
                parts.append(pil_img)
            except Exception as e:
                print(f"[Gemini] Imagem inválida ignorada: {e}")

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: chat.send_message(parts))
        return resp.text
