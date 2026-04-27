import logging
import os
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import AgentConfig
from app.providers import OpenAIProvider


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    request_id: str


class MetadataResponse(BaseModel):
    app_name: str
    company_name: str
    logo_url: str
    accent_color: str
    accent_color_2: str
    whatsapp_url: str
    calendly_url: str


class LeadRequest(BaseModel):
    name: str
    email: str
    company: str | None = None
    message: str | None = None


class LeadResponse(BaseModel):
    ok: bool
    total_leads: int


class MetricsResponse(BaseModel):
    total_sessions: int
    total_messages: int
    total_leads: int


def build_provider() -> OpenAIProvider:
    cfg = AgentConfig()
    return OpenAIProvider(
        stt_model=cfg.stt_model,
        llm_model=cfg.llm_model,
        tts_model=cfg.tts_model,
        tts_voice=cfg.tts_voice,
        system_prompt=cfg.system_prompt,
    )


cfg = AgentConfig()
app = FastAPI(title=f"{cfg.app_name} API", version="1.1.0")
provider = build_provider()
app.mount("/static", StaticFiles(directory="static"), name="static")
logger = logging.getLogger("voice-agent-api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# In-memory state; move to Redis/Postgres for larger deployments.
session_store: dict[str, list[dict[str, str]]] = defaultdict(list)
ip_windows: dict[str, deque[float]] = defaultdict(deque)
leads: list[dict[str, str]] = []
usage = {"total_messages": 0}


def _enforce_api_key(x_api_key: str | None) -> None:
    if not cfg.client_api_key:
        return
    if x_api_key != cfg.client_api_key:
        raise HTTPException(status_code=401, detail="invalid API key")


def _enforce_rate_limit(client_ip: str) -> None:
    now = time.time()
    window = ip_windows[client_ip]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= cfg.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    window.append(now)


def _enforce_admin_key(x_admin_key: str | None) -> None:
    if not cfg.admin_key:
        return
    if x_admin_key != cfg.admin_key:
        raise HTTPException(status_code=401, detail="invalid admin key")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):  # noqa: ANN001
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s elapsed_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/")
def home() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metadata", response_model=MetadataResponse)
def metadata() -> MetadataResponse:
    return MetadataResponse(
        app_name=cfg.app_name,
        company_name=cfg.company_name,
        logo_url=cfg.logo_url,
        accent_color=cfg.accent_color,
        accent_color_2=cfg.accent_color_2,
        whatsapp_url=cfg.whatsapp_url,
        calendly_url=cfg.calendly_url,
    )


@app.post("/leads", response_model=LeadResponse)
def create_lead(payload: LeadRequest) -> LeadResponse:
    name = payload.name.strip()
    email = payload.email.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="valid email is required")

    lead = {
        "name": name,
        "email": email,
        "company": (payload.company or "").strip(),
        "message": (payload.message or "").strip(),
        "created_at": str(int(time.time())),
    }
    leads.append(lead)
    return LeadResponse(ok=True, total_leads=len(leads))


@app.get("/admin/metrics", response_model=MetricsResponse)
def admin_metrics(x_admin_key: str | None = Header(default=None)) -> MetricsResponse:
    _enforce_admin_key(x_admin_key)
    return MetricsResponse(
        total_sessions=len(session_store),
        total_messages=usage["total_messages"],
        total_leads=len(leads),
    )


@app.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> ChatResponse:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing")
    _enforce_api_key(x_api_key)
    client_ip = request.client.host if request.client else "unknown"
    _enforce_rate_limit(client_ip)
    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    session_id = payload.session_id or str(uuid.uuid4())
    history = session_store[session_id]
    reply = provider.respond(text, conversation=history)

    history.extend(
        [
            {"role": "user", "content": text},
            {"role": "assistant", "content": reply},
        ]
    )
    usage["total_messages"] += 1
    max_messages = max(2, cfg.max_history_turns * 2)
    if len(history) > max_messages:
        session_store[session_id] = history[-max_messages:]

    request_id = getattr(request.state, "request_id", "n/a")
    return ChatResponse(reply=reply, session_id=session_id, request_id=request_id)
