import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional

from services.ai_providers import AIProviderService, PROVIDERS_META
from services.rag import RAGService
from services.web_search import WebSearchService

BASE_DIR = Path(__file__).parent
STUDY_DIR = BASE_DIR / "study_materials"
CONFIG_FILE = BASE_DIR / "config.json"
STATIC_DIR = BASE_DIR / "static"
ALLOWED_EXT = {".pdf", ".docx", ".txt", ".md"}

STUDY_DIR.mkdir(exist_ok=True)

rag = RAGService(STUDY_DIR)
ai_svc = AIProviderService()
search_svc = WebSearchService()


def load_cfg() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"providers": {}, "default_provider": ""}


def save_cfg(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _safe_path(filename: str) -> Path:
    resolved = (STUDY_DIR / filename).resolve()
    if not resolved.is_relative_to(STUDY_DIR.resolve()):
        raise HTTPException(400, "Nome de arquivo inválido")
    return resolved


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cfg = load_cfg()
    for prov, data in cfg.get("providers", {}).items():
        if data.get("api_key"):
            ai_svc.update_provider(prov, data["api_key"], data.get("model"))
    for f in STUDY_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in ALLOWED_EXT and not rag.is_indexed(f.name):
            asyncio.create_task(rag.index_document(f))
    yield


app = FastAPI(title="Professor Pardal", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    images: Optional[List[str]] = []
    search_mode: str = "materials"   # internet | materials | both
    history: Optional[List[Dict]] = []
    provider: Optional[str] = None
    model: Optional[str] = None


class KeyUpdate(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None


class DefaultProvider(BaseModel):
    provider: str


# ── Static / root ─────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ── Config endpoints ──────────────────────────────────────────────────────────

@app.get("/api/config")
async def get_config():
    cfg = load_cfg()
    providers_status = {}
    for k, meta in PROVIDERS_META.items():
        stored = cfg.get("providers", {}).get(k, {})
        key = stored.get("api_key", "")
        providers_status[k] = {
            **meta,
            "configured": bool(key),
            "api_key_hint": f"···{key[-4:]}" if len(key) >= 4 else ("" if not key else "···"),
            "selected_model": stored.get("model") or meta["default_model"],
        }
    return {
        "providers": providers_status,
        "default_provider": cfg.get("default_provider", ""),
    }


@app.post("/api/config/key")
async def update_key(body: KeyUpdate):
    cfg = load_cfg()
    cfg.setdefault("providers", {})[body.provider] = {
        "api_key": body.api_key,
        "model": body.model,
    }
    if not cfg.get("default_provider"):
        cfg["default_provider"] = body.provider
    save_cfg(cfg)
    ai_svc.update_provider(body.provider, body.api_key, body.model)
    return {"status": "ok"}


@app.post("/api/config/default")
async def set_default(body: DefaultProvider):
    cfg = load_cfg()
    cfg["default_provider"] = body.provider
    save_cfg(cfg)
    return {"status": "ok"}


# ── Documents endpoints ────────────────────────────────────────────────────────

@app.get("/api/documents")
async def list_docs():
    docs = []
    for f in sorted(STUDY_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXT:
            docs.append({
                "name": f.name,
                "size": f.stat().st_size,
                "indexed": rag.is_indexed(f.name),
                "indexing": rag.is_indexing(f.name),
            })
    return {"documents": docs}


@app.post("/api/documents/upload")
async def upload_doc(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(400, f"Tipo não suportado. Use: {', '.join(ALLOWED_EXT)}")
    dest = STUDY_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)
    asyncio.create_task(rag.index_document(dest))
    return {"status": "ok", "filename": file.filename}


@app.delete("/api/documents/{filename}")
async def delete_doc(filename: str):
    path = _safe_path(filename)
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    path.unlink()
    rag.remove_document(filename)
    return {"status": "ok"}


@app.post("/api/documents/{filename}/reindex")
async def reindex_doc(filename: str):
    path = _safe_path(filename)
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    asyncio.create_task(rag.index_document(path))
    return {"status": "indexando"}


# ── Chat endpoint ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é Pardal, assistente de estudos preciso e confiável do Professor Pardal.

Regras invioláveis:
1. NUNCA invente informações. Baseie-se APENAS nas fontes fornecidas no contexto.
2. Ao usar material de estudo, cite SEMPRE no formato: 📚 *[Nome do documento], p. X, §Y*
3. Se a resposta não estiver nas fontes disponíveis, diga explicitamente que não encontrou.
4. Seja preciso, claro e didático. Responda sempre em português do Brasil.
5. Ao citar trechos, use aspas e indique a fonte imediatamente após.
6. Quando usar resultados da internet, cite a URL da fonte.
"""


@app.post("/api/chat")
async def chat(req: ChatRequest):
    cfg = load_cfg()
    provider = req.provider or cfg.get("default_provider", "")
    if not provider:
        raise HTTPException(400, "Nenhum provedor de IA configurado. Configure nas Configurações.")

    prov_cfg = cfg.get("providers", {}).get(provider, {})
    api_key = prov_cfg.get("api_key", "")
    if not api_key:
        raise HTTPException(400, f"Chave API para '{provider}' não configurada.")

    model = req.model or prov_cfg.get("model") or None
    context_parts: List[str] = []
    citations: List[Dict] = []
    web_results: List[Dict] = []

    # RAG search
    if req.search_mode in ("materials", "both"):
        hits = await rag.search(req.message, top_k=6)
        if hits:
            context_parts.append("## Conteúdo dos seus materiais de estudo:\n")
            for i, h in enumerate(hits, 1):
                context_parts.append(
                    f"[Fonte {i} | {h['source']} | p.{h['page']} | §{h['paragraph']}]\n{h['text']}\n"
                )
                citations.append(h)

    # Web search
    if req.search_mode in ("internet", "both"):
        web_results = await search_svc.search(req.message, max_results=5)
        if web_results:
            context_parts.append("\n## Resultados da busca na internet:\n")
            for r in web_results:
                context_parts.append(
                    f"- **{r['title']}** — {r['url']}\n  {r['snippet']}\n"
                )

    system = SYSTEM_PROMPT
    if context_parts:
        system += "\n\n" + "\n".join(context_parts)

    messages = list(req.history) + [{"role": "user", "content": req.message}]

    try:
        response = await ai_svc.chat(
            provider=provider,
            api_key=api_key,
            model=model,
            system=system,
            messages=messages,
            images=req.images or [],
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "A IA não respondeu em 30 segundos. Se sua cota estiver esgotada, aguarde alguns minutos e tente novamente.")
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower() or "rate" in err.lower() or "ResourceExhausted" in type(e).__name__:
            raise HTTPException(429, "Limite de requisições da API atingido. Aguarde alguns minutos e tente novamente.")
        if "401" in err or "403" in err or "authentication" in err.lower() or "api_key" in err.lower() or "api key" in err.lower():
            raise HTTPException(401, "Chave de API inválida ou sem permissão. Verifique nas Configurações.")
        raise HTTPException(502, f"Erro no provedor de IA ({type(e).__name__}): {err[:300]}")

    return {"response": response, "citations": citations, "web_results": web_results}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
