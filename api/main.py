"""
ERSim API — FastAPI + WebSockets

Endpoints:
  POST /session           create a new game session, returns session_id
  WS   /session/{id}      bidirectional game channel
  GET  /session/{id}/status  lightweight polling fallback

Run with:
  cd ERSim
  .venv/bin/uvicorn api.main:app --reload --port 8000
"""

import asyncio
import json
import io
import os
from contextlib import redirect_stdout

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .session import create_session, get_session, remove_session
from .commands import process_command
from .ticker import tick_loop


app = FastAPI(title="ERSim API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup — launch background ticker
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup():
    asyncio.create_task(tick_loop())


# ---------------------------------------------------------------------------
# REST: create session
# ---------------------------------------------------------------------------

@app.post("/session")
async def new_session(num_bays: int = 3, model: str = "anthropic/claude-haiku-4-5"):
    """
    Create a new game session.
    Returns session_id and the shift start text.
    """
    session = create_session(num_bays=num_bays, model=model)

    # Capture shift.setup() stdout (it prints the shift start banner)
    buf = io.StringIO()
    with redirect_stdout(buf):
        session.shift.setup()
    start_text = buf.getvalue()

    return {
        "session_id": session.session_id,
        "start_text": start_text,
        "bays": [
            {
                "bay_id": bay_id,
                "patient_name": bay.patient_name,
                "acuity": bay.acuity,
                "triage_summary": bay.triage_summary,
                "resident": bay.resident.name,
            }
            for bay_id, bay in session.shift.bays.items()
        ],
    }


# ---------------------------------------------------------------------------
# WebSocket: game channel
# ---------------------------------------------------------------------------

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

    # Send current status on connect
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

            # Capture any print() calls the shift engine makes
            buf = io.StringIO()
            with redirect_stdout(buf):
                await process_command(session, command)
            leftover = buf.getvalue().strip()
            if leftover:
                await session.send_text(leftover, source="system")

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
