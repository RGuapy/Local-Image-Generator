import json
import threading
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import CLEANUP_INTERVAL_SECONDS, TOKEN_FILE
from app.voice_generator import (
    cleanup_old_voice_tasks,
    create_voice_task,
    get_voice_output_path,
    get_voice_task,
    start_voice_worker,
)
from app.voice_models import VoiceGenerateRequest, VoiceStatusResponse, VoiceTaskResponse

_api_token: str = ""
_bearer = HTTPBearer()


def _load_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"Token file not found: {TOKEN_FILE}. "
            "Create it on the server with a secret value before starting."
        )
    token = TOKEN_FILE.read_text().strip()
    if not token:
        raise RuntimeError(f"Token file {TOKEN_FILE} is empty.")
    return token


async def _verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> None:
    if credentials.credentials != _api_token:
        raise HTTPException(status_code=401, detail="Invalid token")


def _cleanup_worker():
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        cleanup_old_voice_tasks()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _api_token
    _api_token = _load_token()
    threading.Thread(target=_cleanup_worker, daemon=True).start()
    start_voice_worker()
    yield


app = FastAPI(title="Local Image Generator", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/voice/generate", response_model=VoiceTaskResponse, dependencies=[Depends(_verify_token)])
async def voice_generate(request: VoiceGenerateRequest):
    task = create_voice_task(request.text, request.language, request.exaggeration)
    return VoiceTaskResponse(task_id=task.task_id, status=task.status)


@app.get("/voice/status/{task_id}", response_model=VoiceStatusResponse, dependencies=[Depends(_verify_token)])
async def voice_status(task_id: str):
    task = get_voice_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return VoiceStatusResponse(task_id=task.task_id, status=task.status, error=task.error)


@app.get("/voice/download/{task_id}", dependencies=[Depends(_verify_token)])
async def voice_download(task_id: str):
    task = get_voice_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "completed":
        raise HTTPException(status_code=404, detail="Task not completed")
    output_path = get_voice_output_path(task_id)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    timestamps = json.dumps([t.model_dump() for t in (task.timestamps or [])])
    return FileResponse(
        path=str(output_path),
        media_type="audio/wav",
        filename=f"{task_id}.wav",
        headers={"X-Timestamps": timestamps},
    )


