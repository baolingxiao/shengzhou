# -*- coding: utf-8 -*-
"""贾维斯 · Neural Pal 本地对话 API（对接 NeuralInterface 前端）。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from neuralpal.characters.constants import DEFAULT_CHARACTER_ID, DEFAULT_SESSION_ID
from neuralpal.characters.store import get_character_store
from neuralpal.config import get_settings
from neuralpal.llm.llm_router import NeuralPalChatOrchestrator
from neuralpal.memory.admin_service import (
    bootstrap_character_memory_maintenance,
    serialize_messages,
)
from neuralpal.memory.character_palace import palace_paths_for_character_id
from neuralpal.memory.memory_system import NeuralPalMemoryPalaceOrchestrator
from server.auth import authenticate
from server.memory_routes import attach_chat_admin_routes, attach_memory_message_routes, router as admin_router
from server.trust_routes import router as trust_router
from server.system_routes import router as system_router
from server.trace_routes import router as trace_router
from server.voice_service import VoiceService

logger = logging.getLogger(__name__)


@dataclass
class ReplyPayload:
    text: str
    route: str = "general"
    blocked: bool = False
    pending_action: dict | None = None
    action_status: str | None = None
    action_task_id: str | None = None
    work_mode: str | None = None
    trust_delta: int | None = None
    trust_points: int | None = None
    segments: list[str] | None = None
    trace_id: str | None = None


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1)
    session_id: str = Field(default=DEFAULT_SESSION_ID)
    character_id: str | None = Field(default=None)
    trace_id: str | None = Field(default=None)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class CharacterInfo(BaseModel):
    id: str
    name: str
    ai_type: str
    user_mbti: str


class ChatService:
    def __init__(self) -> None:
        settings = get_settings()
        self._use_memory = bool(settings.local_web_use_memory_orchestrator)
        self._memory_orch: dict[str, NeuralPalMemoryPalaceOrchestrator] = {}
        self._basic_orch: dict[str, NeuralPalChatOrchestrator] = {}
        self._orch_character: dict[str, str] = {}
        self._lock = threading.Lock()
        self._maintenance_bootstrapped = False

    def _session(self, raw: str) -> str:
        sid = (raw or DEFAULT_SESSION_ID).strip()
        return sid[:120] or DEFAULT_SESSION_ID

    def _bootstrap_maintenance_once(self) -> None:
        if self._maintenance_bootstrapped or not self._use_memory:
            return
        self._maintenance_bootstrapped = True
        bootstrap_character_memory_maintenance(DEFAULT_CHARACTER_ID)

    def _get_orchestrator(
        self,
        session_id: str,
        *,
        character_id: str | None = None,
    ):
        sid = self._session(session_id)
        cid = (character_id or DEFAULT_CHARACTER_ID).strip()
        self._bootstrap_maintenance_once()

        if self._use_memory:
            bound = self._orch_character.get(sid)
            if sid in self._memory_orch and bound and bound != cid:
                self._memory_orch.pop(sid, None)
            if sid not in self._memory_orch:
                palace_root, chroma_path, _ = palace_paths_for_character_id(cid)
                self._memory_orch[sid] = NeuralPalMemoryPalaceOrchestrator(
                    verbose=False,
                    palace_root=palace_root,
                    chroma_path=chroma_path,
                    run_maintenance_on_init=False,
                )
                self._orch_character[sid] = cid
            return self._memory_orch[sid]

        if sid not in self._basic_orch:
            self._basic_orch[sid] = NeuralPalChatOrchestrator(
                verbose=False,
                use_rules_layer_preamble=True,
            )
        return self._basic_orch[sid]

    async def chat(
        self,
        session_id: str,
        text: str,
        *,
        character_id: str | None = None,
    ) -> ReplyPayload:
        cid = (character_id or DEFAULT_CHARACTER_ID).strip()
        try:
            with self._lock:
                orch = self._get_orchestrator(session_id, character_id=cid)
            result = await asyncio.to_thread(
                orch.chat_turn,
                text.strip(),
                session_id=self._session(session_id),
                character_id=cid,
            )
            blocked = bool(
                getattr(result, "blocked_by_preflight", False)
                or getattr(result, "blocked", False)
            )
            return ReplyPayload(
                text=result.text,
                route=getattr(result, "route", "general"),
                blocked=blocked,
                pending_action=getattr(result, "pending_action", None),
                action_status=getattr(result, "action_status", None),
                action_task_id=getattr(result, "action_task_id", None),
                work_mode=getattr(result, "work_mode", None),
                trust_delta=getattr(result, "trust_delta", None),
                trust_points=getattr(result, "trust_points", None),
                segments=getattr(result, "segments", None),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"处理失败：{type(exc).__name__}: {exc}",
            ) from exc

    def reset_session(self, session_id: str) -> None:
        sid = self._session(session_id)
        with self._lock:
            self._memory_orch.pop(sid, None)
            self._basic_orch.pop(sid, None)
            self._orch_character.pop(sid, None)

    def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        sid = self._session(session_id)
        with self._lock:
            orch = self._memory_orch.get(sid) or self._basic_orch.get(sid)
        if orch is None:
            return []
        if hasattr(orch, "_short"):
            messages = list(orch._short.chat_memory.messages)
        elif hasattr(orch, "_history"):
            messages = list(orch._history)
        else:
            return []
        return serialize_messages(messages)

    def delete_live_messages(
        self,
        session_id: str,
        indices: list[int],
        *,
        character_id: str | None = None,
    ) -> dict[str, object]:
        """删除当前会话内存中的指定消息，并同步短期记忆文件。"""
        from neuralpal.memory.admin_service import character_palace_scope
        from neuralpal.memory.memory_chat_edit import delete_messages_at_indices, _to_langchain_messages
        from neuralpal.memory.palace_layout import _safe_session_slug, path_short, sync_short_term_snapshot
        from neuralpal.memory.palace_browser import delete_palace_memory

        sid = self._session(session_id)
        cid = (character_id or DEFAULT_CHARACTER_ID).strip()
        palace_root, _, char_name = palace_paths_for_character_id(cid)

        with self._lock:
            orch = self._memory_orch.get(sid)
            if orch is None or not hasattr(orch, "_short"):
                rel = f"01_短期记忆/{_safe_session_slug(sid)}.md"
                return delete_messages_at_indices(
                    palace_root=palace_root,
                    rel_path=rel,
                    indices=indices,
                )

            msgs = list(orch._short.chat_memory.messages)
            to_remove = sorted({int(i) for i in indices if 0 <= int(i) < len(msgs)}, reverse=True)
            if not to_remove:
                raise ValueError("无效的消息下标")

            for idx in to_remove:
                msgs.pop(idx)
            orch._short.chat_memory.messages = msgs
            rolled = list(getattr(orch, "_rolled_summaries", []) or [])

            rel = f"01_短期记忆/{_safe_session_slug(sid)}.md"
            fp = path_short(palace_root) / f"{_safe_session_slug(sid)}.md"

            if not msgs:
                if fp.is_file():
                    with character_palace_scope(char_name):
                        delete_palace_memory(fp.resolve())
                return {
                    "deleted_count": len(to_remove),
                    "remaining": 0,
                    "file_removed": True,
                    "session_id": sid,
                }

            sync_short_term_snapshot(
                session_id=sid,
                messages=msgs,
                rolled_summaries=rolled or None,
                palace_root=palace_root,
            )
            return {
                "deleted_count": len(to_remove),
                "remaining": len(msgs),
                "file_removed": False,
                "session_id": sid,
                "rel_path": rel,
            }

    def sync_orchestrator_after_file_edit(self, session_id: str) -> None:
        """短期记忆文件变更后，刷新已加载编排器的内存消息。"""
        from neuralpal.memory.memory_chat_edit import _to_langchain_messages, parse_memory_chat_messages
        from neuralpal.memory.palace_layout import _safe_session_slug, path_short

        sid = self._session(session_id)
        with self._lock:
            orch = self._memory_orch.get(sid)
            if orch is None or not hasattr(orch, "_short"):
                return
            palace_root = orch._palace_root
            fp = path_short(palace_root) / f"{_safe_session_slug(sid)}.md"
            if not fp.is_file():
                orch._short.chat_memory.clear()
                return
            body = fp.read_text(encoding="utf-8")
            parsed = parse_memory_chat_messages(body)
            orch._short.chat_memory.messages = _to_langchain_messages(parsed)


app = FastAPI(title="贾维斯 Neural Pal Chat")
_app_port = os.environ.get("NEURALPAL_BACKEND_PORT", "8766")
_cors_origins = [
    "http://127.0.0.1:5190",
    "http://localhost:5190",
    "http://127.0.0.1:5191",
    "http://localhost:5191",
    "http://127.0.0.1:5192",
    "http://localhost:5192",
    "http://127.0.0.1:5193",
    "http://localhost:5193",
]
if os.environ.get("JARVIS_APP_MODE") == "1":
    _cors_origins.extend(
        [
            f"http://127.0.0.1:{_app_port}",
            f"http://localhost:{_app_port}",
        ]
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
service = ChatService()
voice_service = VoiceService()

attach_chat_admin_routes(admin_router, service)
attach_memory_message_routes(admin_router, service)
app.include_router(admin_router)
app.include_router(trust_router)
app.include_router(system_router)
app.include_router(trace_router)


@app.on_event("startup")
async def _startup_shenzhou_scheduler() -> None:
    try:
        from neuralpal.shenzhou.scheduler import start_shenzhou_scheduler

        start_shenzhou_scheduler()
    except Exception:
        logger.exception("shenzhou scheduler startup failed")


@app.post("/api/shenzhou/sync-user-day")
async def api_shenzhou_sync_user_day(
    session_id: str = DEFAULT_SESSION_ID,
) -> dict[str, object]:
    """手动触发：将今日用户对话同步到沈昼世界模型。"""
    from neuralpal.shenzhou.scheduler import job_sync_user_day

    return job_sync_user_day(session_id)


@app.post("/api/shenzhou/pull-life-context")
async def api_shenzhou_pull_life_context() -> dict[str, object]:
    """手动触发：从世界引擎拉取今日生活上下文并缓存。"""
    from neuralpal.shenzhou.scheduler import job_pull_life_context

    return job_pull_life_context()


@app.post("/api/shenzhou/run-pipeline")
async def api_shenzhou_run_pipeline() -> dict[str, object]:
    """手动触发：世界引擎每日流水线（背景优化 + 模拟）。"""
    from neuralpal.shenzhou.scheduler import job_world_daily_pipeline

    return job_world_daily_pipeline()


@app.get("/api/shenzhou/status")
async def api_shenzhou_status() -> dict[str, object]:
    from neuralpal.config import get_settings
    from neuralpal.shenzhou.client import ping

    s = get_settings()
    return {
        "enabled": s.shenzhou_integration_enabled,
        "world_api_url": s.shenzhou_world_api_url,
        "reachable": ping() if s.shenzhou_integration_enabled else False,
        "user_entity_slug": s.shenzhou_user_entity_slug,
        "schedule": {
            "sync": f"{s.shenzhou_sync_hour:02d}:{s.shenzhou_sync_minute:02d}",
            "pipeline": f"{s.shenzhou_pipeline_hour:02d}:{s.shenzhou_pipeline_minute:02d}",
            "pull": f"{s.shenzhou_pull_hour:02d}:{s.shenzhou_pull_minute:02d}",
            "timezone": s.shenzhou_timezone,
        },
    }


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/login")
async def api_login(payload: LoginRequest) -> dict[str, object]:
    user = authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"ok": True, "username": user.username, "is_admin": user.is_admin}


@app.get("/api/character", response_model=CharacterInfo)
async def get_character(character_id: str = DEFAULT_CHARACTER_ID) -> CharacterInfo:
    char = get_character_store().get_character(character_id.strip())
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    return CharacterInfo(
        id=char.id,
        name=char.name,
        ai_type=char.ai_type,
        user_mbti=char.user_mbti,
    )


@app.post("/api/chat")
async def api_chat(
    payload: ChatRequest,
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> dict[str, object]:
    from neuralpal.trace import ExecutionTraceRecorder, new_trace_id, trace_scope

    trace_id = (payload.trace_id or x_trace_id or new_trace_id()).strip()
    cid = (payload.character_id or DEFAULT_CHARACTER_ID).strip()
    recorder = ExecutionTraceRecorder(
        trace_id,
        user_input=payload.text,
        session_id=payload.session_id,
        character_id=cid,
    )
    logger.info("[TRACE] %s", trace_id)
    recorder.record_backend_received()

    with trace_scope(recorder):
        try:
            result = await service.chat(
                payload.session_id,
                payload.text,
                character_id=payload.character_id,
            )
            resp = asdict(result)
            resp["trace_id"] = trace_id
            recorder.record_api_response(resp)
            recorder.save()
            return resp
        except HTTPException:
            recorder.record_error("api_chat", "HTTPException")
            recorder.save()
            raise
        except Exception as exc:
            recorder.record_error("api_chat", str(exc), exc_type=type(exc).__name__)
            recorder.save()
            raise


class ResetRequest(BaseModel):
    session_id: str = Field(default=DEFAULT_SESSION_ID)


class DebugTracePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    seq: int = 0
    level: str = "info"
    session: str = ""
    checkpoint: str = ""
    url: str = ""
    loadCount: int = 0
    ts: str = ""


@app.post("/api/debug/trace")
async def api_debug_trace(payload: DebugTracePayload) -> dict[str, bool]:
    level = payload.level.upper()
    marker = "!!!" if level == "ALERT" else ("?" if level == "WARN" else " ")
    line = (
        f"[JARVIS-TRACE{marker}] #{payload.seq:04d} "
        f"session={payload.session} load={payload.loadCount} "
        f"{payload.checkpoint}"
    )
    extra = payload.model_dump(
        exclude={"seq", "level", "session", "checkpoint", "loadCount", "ts", "url"}
    )
    if payload.url:
        extra["url"] = payload.url
    if payload.ts:
        extra["ts"] = payload.ts
    if extra:
        line += " | " + json.dumps(extra, ensure_ascii=False)
    print(line, flush=True)
    return {"ok": True}


@app.post("/api/reset")
async def api_reset(payload: ResetRequest | None = None) -> dict[str, bool]:
    sid = payload.session_id if payload else DEFAULT_SESSION_ID
    service.reset_session(sid)
    return {"ok": True}


class AgentSessionRequest(BaseModel):
    session_id: str = Field(default=DEFAULT_SESSION_ID)
    character_id: str | None = Field(default=None)


@app.get("/api/agent/pending")
async def api_agent_pending(session_id: str = DEFAULT_SESSION_ID) -> dict[str, object]:
    from neuralpal.tools.agent.pending import load_pending

    pending = load_pending(session_id.strip())
    if pending is None:
        return {"ok": True, "pending": None}
    return {"ok": True, "pending": pending.to_dict()}


@app.post("/api/agent/confirm")
async def api_agent_confirm(payload: AgentSessionRequest) -> dict[str, object]:
    from neuralpal.tools.agent.preprocess import preprocess_agent_turn

    pre = preprocess_agent_turn(
        "确认",
        session_id=payload.session_id.strip(),
        character_id=payload.character_id,
    )
    return {
        "ok": True,
        "handled": pre.handled,
        "pending_action": pre.pending_action,
        "execution_summary": pre.execution_summary,
        "system_note": pre.system_note,
    }


@app.post("/api/agent/cancel")
async def api_agent_cancel(payload: AgentSessionRequest) -> dict[str, object]:
    from neuralpal.tools.agent.pending import clear_pending, load_pending

    sid = payload.session_id.strip()
    pending = load_pending(sid)
    if pending is None:
        return {"ok": True, "cancelled": False, "message": "无待取消任务"}
    clear_pending(sid)
    return {"ok": True, "cancelled": True, "task_id": pending.task_id}


class TtsRequest(BaseModel):
    text: str = Field(..., min_length=1)
    trace_id: str | None = Field(default=None)


class RealtimeSessionRequest(BaseModel):
    character_id: str | None = Field(default=None)
    session_id: str = Field(default=DEFAULT_SESSION_ID)
    mode: str = Field(default="voice_chat")


@app.post("/api/realtime/session")
async def api_realtime_session(payload: RealtimeSessionRequest) -> dict[str, object]:
    from server.realtime_service import create_realtime_session

    try:
        result = await asyncio.to_thread(
            create_realtime_session,
            character_id=payload.character_id,
            session_id=payload.session_id,
            mode=payload.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[RealtimeSession] error")
        raise HTTPException(
            status_code=500,
            detail=f"Realtime 会话创建失败：{type(exc).__name__}",
        ) from exc

    return {
        "client_secret": result.client_secret,
        "model": result.model,
        "voice": result.voice,
        "expires_at": result.expires_at,
        "session_id": result.session_id,
    }


@app.get("/api/voice/status")
async def api_voice_status() -> dict[str, object]:
    status = voice_service.status()
    return {
        "stt_available": status.stt_available,
        "stt_provider": status.stt_provider,
        "stt_model": status.stt_model,
        "stt_reason": status.stt_reason,
        "tts_available": status.tts_available,
        "tts_reason": status.tts_reason,
        "wake_phrases": list(status.wake_phrases),
        "silence_seconds": status.silence_seconds,
        "min_speech_seconds": status.min_speech_seconds,
        "wake_timeout_seconds": status.wake_timeout_seconds,
        "followup_seconds": status.followup_seconds,
        "wake_max_seconds": status.wake_max_seconds,
        "wake_stt_max_seconds": status.wake_stt_max_seconds,
        "wake_silence_seconds": status.wake_silence_seconds,
    }


@app.post("/api/voice/stt")
async def api_voice_stt(
    audio: UploadFile = File(...),
    purpose: str = Form(default="utterance"),
) -> dict[str, object]:
    wav_bytes = await audio.read()
    if not wav_bytes:
        raise HTTPException(status_code=400, detail="音频为空")
    try:
        result = await voice_service.transcribe_wav_async(wav_bytes, purpose=purpose.strip() or "utterance")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "text": result.text,
        "wake_phrase": result.wake_phrase,
        "cleaned_text": result.cleaned_text,
        "is_wake_only": result.is_wake_only,
    }


@app.post("/api/voice/tts")
async def api_voice_tts(
    payload: TtsRequest,
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> dict[str, object]:
    from neuralpal.trace import get_trace
    from neuralpal.trace.context import set_trace
    from neuralpal.trace.recorder import ExecutionTraceRecorder

    trace_id = (payload.trace_id or x_trace_id or "").strip()
    if trace_id:
        recorder = ExecutionTraceRecorder.from_existing(trace_id)
        set_trace(recorder)
        logger.info("[TRACE] tts %s", trace_id)

    try:
        chunks = await voice_service.synthesize_async(payload.text.strip())
    except ValueError as exc:
        if trace_id and get_trace():
            get_trace().record_error("tts", str(exc), exc_type=type(exc).__name__)
            get_trace().save()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if trace_id and get_trace():
            get_trace().record_error("tts", str(exc), exc_type=type(exc).__name__)
            get_trace().save()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if trace_id and get_trace():
        get_trace().save()

    return {
        "trace_id": trace_id or None,
        "chunks": [
            {
                "index": chunk.index,
                "audio_base64": chunk.audio_base64,
                "mime_type": chunk.mime_type,
            }
            for chunk in chunks
        ],
    }


def _resolve_frontend_dist() -> Path | None:
    """App 模式：同一端口提供前端 PWA（8766），无需单独 Vite 端口。"""
    if os.environ.get("JARVIS_APP_MODE") != "1":
        return None
    candidates: list[Path] = [
        ROOT / "dist",
        ROOT / "project" / "dist",
    ]
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        resources = exe.parent.parent / "Resources"
        candidates[:0] = [resources / "project" / "dist", resources / "dist"]
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


_FRONTEND_DIST = _resolve_frontend_dist()
if _FRONTEND_DIST is not None:

    @app.get("/")
    async def spa_index() -> FileResponse:
        return FileResponse(_FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        target = (_FRONTEND_DIST / full_path).resolve()
        try:
            target.relative_to(_FRONTEND_DIST.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        if target.is_file():
            return FileResponse(target)
        return FileResponse(_FRONTEND_DIST / "index.html")


def main() -> None:
    port = int(os.environ.get("NEURALPAL_BACKEND_PORT", "8766"))
    host = os.environ.get("NEURALPAL_BIND", "127.0.0.1")
    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
