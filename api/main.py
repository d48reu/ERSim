"""
ERSim API — FastAPI + WebSockets

Endpoints:
  POST /session           create a new game session, returns session_id
  WS   /session/{id}      bidirectional game channel
  GET  /session/{id}/status  lightweight polling fallback

Run with:
  pip install -e .   # once, from repo root (adds `llm` + packages to env)
  cd ERSim && .venv/bin/uvicorn api.main:app --reload --port 8000
  # or: python run.py
"""

import asyncio
import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from llm import _detect_backend, get_model

from cases.demo_cases import get_demo_case_meta
from .session import create_session, get_session, remove_session
from .commands import process_command
from .ticker import tick_loop
from .feedback_store import (
    export_feedback_csv,
    get_build_version,
    init_feedback_db,
    save_feedback,
)
from residents.resident import build_initial_resident_state


def _cors_settings() -> tuple[list[str], bool]:
    """
    CORS for API + WebSocket upgrade.
    Set ERSIM_CORS_ORIGINS to a comma-separated list for production
    (e.g. https://your-service.onrender.com). Empty → wildcard without credentials
    (valid for same-origin static + local Vite proxy).
    """
    raw = os.environ.get("ERSIM_CORS_ORIGINS", "").strip()
    if raw:
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        return origins, True
    return ["*"], False


_origins, _creds = _cors_settings()

app = FastAPI(title="ERSim API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup — launch background ticker
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup():
    init_feedback_db()
    asyncio.create_task(tick_loop())


# ---------------------------------------------------------------------------
# REST: create session
# ---------------------------------------------------------------------------

@app.post("/session")
async def new_session(num_bays: int = 3, model: str | None = None):
    """
    Create a new game session.
    Model defaults based on ERSIM_BACKEND (ollama or openrouter).
    Returns session_id and bay info immediately.
    Shift setup (LLM calls for resident openings) runs in background.
    """
    resolved_model = get_model("gameplay", override=model)
    session = create_session(num_bays=num_bays, model=resolved_model)

    # Return immediately with bay info + roster — setup runs async
    return {
        "session_id": session.session_id,
        "start_text": "",  # Will be sent over WebSocket when setup completes
        "status": "setting_up",
        "experience_mode": "flagship",
        "build_version": get_build_version(),
        "bays": [
            {
                "bay_id": bay_id,
                "patient_name": bay.patient_name,
                "acuity": bay.acuity,
                "triage_summary": bay.triage_summary,
                "resident": bay.resident.name,
                "demo_title": get_demo_case_meta(bay.case.case_id).get("title"),
            }
            for bay_id, bay in session.shift.bays.items()
        ],
        "roster": session.shift.get_roster_info(),
    }


class FeedbackMetrics(BaseModel):
    disposition_accuracy: float | None = None
    resolved_cases: int | None = None
    total_cases: int | None = None
    clinical_depth: float | None = None
    trap_cases_fully_caught: int | None = None
    trap_cases_partially_recovered: int | None = None
    autonomous_actions: int | None = None
    warnings_heeded: int | None = None
    attention_distribution: str | None = None


class FeedbackSubmission(BaseModel):
    session_id: str
    build_version: str
    shift_mode: str
    debrief_grade: str
    tester_role: str
    overall_rating: int = Field(ge=1, le=5)
    best_moment: str = Field(min_length=1)
    most_confusing_part: str = Field(min_length=1)
    would_you_use_again: bool
    optional_contact: str = ""
    timestamp: str | None = None
    metrics: FeedbackMetrics


@app.post("/feedback")
async def submit_feedback(payload: FeedbackSubmission):
    row_id = save_feedback(payload.model_dump())
    return {"ok": True, "id": row_id}


@app.get("/feedback/export", response_class=PlainTextResponse)
async def export_feedback(token: str):
    export_token = os.environ.get("ERSIM_FEEDBACK_EXPORT_TOKEN", "").strip()
    if not export_token or token != export_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    return export_feedback_csv()


# ---------------------------------------------------------------------------
# WebSocket: game channel
# ---------------------------------------------------------------------------

def _run_setup_sync(session):
    """Run shift setup in a thread (blocking LLM calls)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        session.shift.setup()
    return buf.getvalue()


async def _run_setup_with_progress(session):
    """Run setup while streaming bay-by-bay progress over the websocket."""
    shift = session.shift
    shift_context, setup_jobs = shift.prepare_setup_jobs()
    total = len(setup_jobs)
    completed = 0
    await session.send("setup_progress", {
        "completed": 0,
        "total": total,
        "current_bay": None,
    })

    def _build_for_bay(job):
        bay_id, resident, case, trap_context = job
        resident_ai, assessment = build_initial_resident_state(
            resident,
            case,
            shift.model,
            shift_context,
            trap_context,
        )
        return bay_id, resident_ai, assessment

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=min(4, max(1, total))) as executor:
        futures = [
            loop.run_in_executor(executor, _build_for_bay, job)
            for job in setup_jobs
        ]

        for future in asyncio.as_completed(futures):
            bay_id, resident_ai, assessment = await future
            shift.apply_setup_result(bay_id, resident_ai, assessment)
            completed += 1
            await session.send("setup_progress", {
                "completed": completed,
                "total": total,
                "current_bay": bay_id,
            })

    return shift._render_shift_start()


@app.websocket("/session/{session_id}")
async def game_socket(websocket: WebSocket, session_id: str):
    """
    Bidirectional game channel.

    Client sends:
      {"command": "go 1"}
      {"command": "bundle troponin, EKG"}

    Server pushes:
      {"type": "message", "text": "...", "source": "system|patient|resident|chart"}
      {"type": "result",  "text": "...", "source": "result"}
      {"type": "autonomous", "text": "...", "source": "resident"}
      {"type": "shift_ended", "summary": "..."}
      {"type": "error", "text": "..."}
    """
    session = get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    session.websocket = websocket

    # Run setup in background thread if not already done
    if not session.setup_complete:
        await session.send_text("Setting up shift — generating resident assessments...", source="system")
        try:
            start_text = await _run_setup_with_progress(session)
            session.setup_complete = True
            if start_text.strip():
                await session.send_text(start_text, source="system")
            await session.send_text(session.shift.status(), source="system")
            await session.send("setup_complete", {
                "bays": [
                    {
                        "bay_id": bay_id,
                        "patient_name": bay.patient_name,
                        "acuity": bay.acuity,
                        "status": bay.status.value,
                        "triage_summary": bay.triage_summary,
                        "resident": bay.resident.name,
                        "demo_title": get_demo_case_meta(bay.case.case_id).get("title"),
                    }
                    for bay_id, bay in session.shift.bays.items()
                ],
            })
        except Exception as e:
            await session.send("error", {"text": f"Setup failed: {e}"})
            return
    else:
        await session.send_text(session.shift.status(), source="system")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                command = msg.get("command", "").strip()
            except Exception:
                command = data.strip()

            if not command:
                continue

            # Run command processing — shift calls may block on LLM
            # Use to_thread for the blocking parts
            try:
                await process_command(session, command)
            except Exception as e:
                await session.send("error", {"text": f"Command error: {e}"})

    except WebSocketDisconnect:
        session.websocket = None
    except Exception as e:
        try:
            await session.send("error", {"text": str(e)})
        except Exception:
            pass
        session.websocket = None


# ---------------------------------------------------------------------------
# REST: status fallback (for debugging / simple clients)
# ---------------------------------------------------------------------------

@app.get("/session/{session_id}/status")
async def session_status(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    shift = session.shift
    return {
        "session_id": session_id,
        "global_turn": shift.global_turn,
        "clock": shift._format_clock(shift.global_turn),
        "active_bay": shift.active_bay_id,
        "bays": [
            {
                "bay_id": bay_id,
                "patient_name": bay.patient_name,
                "acuity": bay.acuity,
                "status": bay.status.value,
                "timer_pressure": bay.timer_pressure,
                "pending_results": len(bay.pending_results),
                "resident": bay.resident.name,
                "triage_summary": bay.triage_summary,
                "guidance": shift.get_bay_guidance(bay_id),
                "demo_title": get_demo_case_meta(bay.case.case_id).get("title"),
            }
            for bay_id, bay in shift.bays.items()
        ],
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Serve React frontend (production build)
# Mount last so API routes take priority
# ---------------------------------------------------------------------------

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(_static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_static_dir, "index.html"))
