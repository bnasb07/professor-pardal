import asyncio
import base64
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.ai_providers import AIProviderService, PROVIDERS_META
from services.project_manager import ProjectManager
from services.rag import RAGService
from services.transcription import TranscriptionService, AUDIO_EXT
from services.web_search import WebSearchService

BASE_DIR   = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
STATIC_DIR  = BASE_DIR / "static"

ALLOWED_DOC_EXT   = {".pdf", ".docx", ".txt", ".md"}
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_EXT       = ALLOWED_DOC_EXT | AUDIO_EXT | ALLOWED_IMAGE_EXT

proj_mgr    = ProjectManager(BASE_DIR)
ai_svc      = AIProviderService()
search_svc  = WebSearchService()
transc_svc  = TranscriptionService()
_rag_cache: Dict[str, RAGService] = {}


def _get_rag(project_id: str = None) -> RAGService:
    pid = project_id or proj_mgr.get_active_id()
    if pid not in _rag_cache:
        _rag_cache[pid] = RAGService(
            proj_mgr.materials_dir(pid),
            proj_mgr.db_dir(pid),
        )
    return _rag_cache[pid]


def load_cfg() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"providers": {}, "default_provider": ""}


def save_cfg(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _safe_path(filename: str, project_id: str = None) -> Path:
    mdir = proj_mgr.materials_dir(project_id)
    resolved = (mdir / filename).resolve()
    if not resolved.is_relative_to(mdir.resolve()):
        raise HTTPException(400, "Nome de arquivo inválido")
    return resolved


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cfg = load_cfg()
    for prov, data in cfg.get("providers", {}).items():
        if data.get("api_key"):
            ai_svc.update_provider(prov, data["api_key"], data.get("model"))
    # Index active project documents on startup
    active_id = proj_mgr.get_active_id()
    mdir = proj_mgr.materials_dir(active_id)
    rag  = _get_rag(active_id)
    for f in mdir.iterdir():
        if f.is_file() and f.suffix.lower() in ALLOWED_DOC_EXT and not rag.is_indexed(f.name):
            asyncio.create_task(rag.index_document(f))
    yield


app = FastAPI(title="Professor Pardal", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    images: Optional[List[str]] = []
    search_mode: str = "materials"
    history: Optional[List[Dict]] = []
    provider: Optional[str] = None
    model: Optional[str] = None


class KeyUpdate(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None


class DefaultProvider(BaseModel):
    provider: str


class ProjectCreate(BaseModel):
    name: str
    emoji: Optional[str] = "📁"


class ProjectRename(BaseModel):
    name: str
    emoji: Optional[str] = None


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


# ── Projects endpoints ────────────────────────────────────────────────────────

@app.get("/api/projects")
async def list_projects():
    projects = proj_mgr.list_projects()
    active_id = proj_mgr.get_active_id()
    result = []
    for p in projects:
        result.append({
            **p,
            "active": p["id"] == active_id,
            "doc_count": proj_mgr.doc_count(p["id"], ALLOWED_DOC_EXT),
        })
    return {"projects": result, "active": active_id}


@app.post("/api/projects")
async def create_project(body: ProjectCreate):
    if not body.name.strip():
        raise HTTPException(400, "Nome do projeto é obrigatório.")
    project = proj_mgr.create(body.name, body.emoji or "📁")
    return project


@app.post("/api/projects/{project_id}/activate")
async def activate_project(project_id: str):
    try:
        proj_mgr.set_active(project_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    # Warm up RAG for the newly active project
    mdir = proj_mgr.materials_dir(project_id)
    rag  = _get_rag(project_id)
    for f in mdir.iterdir():
        if f.is_file() and f.suffix.lower() in ALLOWED_DOC_EXT and not rag.is_indexed(f.name):
            asyncio.create_task(rag.index_document(f))
    return {"status": "ok", "active": project_id}


@app.patch("/api/projects/{project_id}")
async def rename_project(project_id: str, body: ProjectRename):
    if not body.name.strip():
        raise HTTPException(400, "Nome não pode ser vazio.")
    proj_mgr.rename(project_id, body.name, body.emoji)
    return {"status": "ok"}


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    try:
        proj_mgr.delete(project_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    # Clean cached RAG instance
    _rag_cache.pop(project_id, None)
    return {"status": "ok"}


# ── Documents endpoints ────────────────────────────────────────────────────────

@app.get("/api/documents")
async def list_docs():
    active_id = proj_mgr.get_active_id()
    mdir = proj_mgr.materials_dir(active_id)
    rag  = _get_rag(active_id)
    docs = []
    for f in sorted(mdir.iterdir()):
        if f.is_file() and f.suffix.lower() in ALLOWED_DOC_EXT:
            docs.append({
                "name": f.name,
                "size": f.stat().st_size,
                "indexed": rag.is_indexed(f.name),
                "indexing": rag.is_indexing(f.name),
            })
    return {"documents": docs, "project": proj_mgr.get_active()}


@app.post("/api/documents/upload")
async def upload_doc(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()

    if suffix in ALLOWED_DOC_EXT:
        return await _upload_document(file, suffix)
    elif suffix in AUDIO_EXT:
        return await _upload_audio(file, suffix)
    elif suffix in ALLOWED_IMAGE_EXT:
        return await _upload_image(file, suffix)
    else:
        raise HTTPException(
            400,
            f"Tipo não suportado. Use: PDF, DOCX, TXT, MD, "
            f"MP3/WAV/OGG/M4A (áudio) ou JPG/PNG/WEBP (imagem)"
        )


async def _upload_document(file: UploadFile, suffix: str):
    active_id = proj_mgr.get_active_id()
    mdir = proj_mgr.materials_dir(active_id)
    dest = mdir / file.filename
    dest.write_bytes(await file.read())
    asyncio.create_task(_get_rag(active_id).index_document(dest))
    return {"status": "ok", "filename": file.filename, "type": "document"}


async def _upload_audio(file: UploadFile, suffix: str):
    cfg = load_cfg()
    openai_key = cfg.get("providers", {}).get("openai", {}).get("api_key", "")

    active_id = proj_mgr.get_active_id()
    mdir = proj_mgr.materials_dir(active_id)

    # Save audio temporarily
    tmp_path = mdir / file.filename
    tmp_path.write_bytes(await file.read())

    try:
        transcript = await transc_svc.transcribe(tmp_path, openai_key)
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(422, str(e))
    finally:
        # Remove source audio (keep only the transcript)
        tmp_path.unlink(missing_ok=True)

    stem = Path(file.filename).stem
    md_name = f"[audio] {stem}.md"
    md_path = mdir / md_name
    md_path.write_text(
        f"> 🎵 *Transcrição de áudio: {file.filename}*\n\n{transcript}",
        encoding="utf-8"
    )
    asyncio.create_task(_get_rag(active_id).index_document(md_path))
    return {"status": "ok", "filename": md_name, "type": "audio"}


async def _upload_image(file: UploadFile, suffix: str):
    cfg = load_cfg()
    provider = cfg.get("default_provider", "")
    if not provider:
        raise HTTPException(400, "Configure um provedor de IA antes de enviar imagens para o conhecimento.")

    prov_cfg = cfg.get("providers", {}).get(provider, {})
    api_key  = prov_cfg.get("api_key", "")
    model    = prov_cfg.get("model") or None

    if not PROVIDERS_META.get(provider, {}).get("supports_vision"):
        raise HTTPException(400, f"O provedor '{provider}' não suporta análise de imagens.")

    raw = await file.read()
    media_type = f"image/{suffix.lstrip('.')}" if suffix != ".jpg" else "image/jpeg"
    image_b64  = f"data:{media_type};base64,{base64.b64encode(raw).decode()}"

    try:
        description = await ai_svc.describe_image(provider, api_key, model, image_b64, file.filename)
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower():
            raise HTTPException(429, "Limite de requisições da API atingido.")
        raise HTTPException(502, f"Erro ao analisar imagem: {err[:200]}")

    active_id = proj_mgr.get_active_id()
    mdir  = proj_mgr.materials_dir(active_id)
    stem  = Path(file.filename).stem
    md_name = f"[imagem] {stem}.md"
    md_path = mdir / md_name
    md_path.write_text(
        f"> 🖼️ *Análise de imagem: {file.filename}*\n\n{description}",
        encoding="utf-8"
    )
    asyncio.create_task(_get_rag(active_id).index_document(md_path))
    return {"status": "ok", "filename": md_name, "type": "image"}


@app.delete("/api/documents/{filename}")
async def delete_doc(filename: str):
    active_id = proj_mgr.get_active_id()
    path = _safe_path(filename, active_id)
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    path.unlink()
    _get_rag(active_id).remove_document(filename)
    return {"status": "ok"}


@app.post("/api/documents/{filename}/reindex")
async def reindex_doc(filename: str):
    active_id = proj_mgr.get_active_id()
    path = _safe_path(filename, active_id)
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    asyncio.create_task(_get_rag(active_id).index_document(path))
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
    api_key  = prov_cfg.get("api_key", "")
    if not api_key:
        raise HTTPException(400, f"Chave API para '{provider}' não configurada.")

    model = req.model or prov_cfg.get("model") or None
    context_parts: List[str] = []
    citations: List[Dict] = []
    web_results: List[Dict] = []

    if req.search_mode in ("materials", "both"):
        active_id = proj_mgr.get_active_id()
        hits = await _get_rag(active_id).search(req.message, top_k=6)
        if hits:
            context_parts.append("## Conteúdo dos seus materiais de estudo:\n")
            for i, h in enumerate(hits, 1):
                context_parts.append(
                    f"[Fonte {i} | {h['source']} | p.{h['page']} | §{h['paragraph']}]\n{h['text']}\n"
                )
                citations.append(h)

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
        if "401" in err or "403" in err or "authentication" in err.lower() or "api_key" in err.lower():
            raise HTTPException(401, "Chave de API inválida ou sem permissão. Verifique nas Configurações.")
        raise HTTPException(502, f"Erro no provedor de IA ({type(e).__name__}): {err[:300]}")

    return {"response": response, "citations": citations, "web_results": web_results}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8765, reload=False)
