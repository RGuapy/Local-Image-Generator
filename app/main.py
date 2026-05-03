import threading
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import CLEANUP_INTERVAL_SECONDS, TOKEN_FILE
from app.generator import cleanup_old_tasks, create_task, get_output_path, get_task
from app.models import GenerateRequest, GenerateResponse, StatusResponse, TaskStatus

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
        cleanup_old_tasks()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _api_token
    _api_token = _load_token()
    thread = threading.Thread(target=_cleanup_worker, daemon=True)
    thread.start()
    yield


app = FastAPI(title="Local Image Generator", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate", response_model=GenerateResponse, dependencies=[Depends(_verify_token)])
async def generate(request: GenerateRequest):
    task = create_task(request)
    return GenerateResponse(task_id=task.task_id, status=task.status)


@app.get("/status/{task_id}", response_model=StatusResponse, dependencies=[Depends(_verify_token)])
async def get_status(task_id: str):
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return StatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        error=task.error,
    )


@app.get("/download/{task_id}", dependencies=[Depends(_verify_token)])
async def download(task_id: str):
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in (TaskStatus.queued, TaskStatus.running):
        raise HTTPException(
            status_code=409,
            detail=f"Task is not yet complete (status: {task.status})",
        )

    if task.status == TaskStatus.failed:
        raise HTTPException(status_code=422, detail=f"Task failed: {task.error}")

    output_path = get_output_path(task_id)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found on disk")

    return FileResponse(
        path=str(output_path),
        media_type="image/png",
        filename=f"{task_id}.png",
    )
