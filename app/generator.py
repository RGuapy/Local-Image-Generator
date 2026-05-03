import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import torch
from diffusers import StableDiffusionPipeline

from app.config import (
    DEVICE,
    ENABLE_ATTENTION_SLICING,
    MODEL_ID,
    OUTPUTS_DIR,
    USE_FLOAT16,
)
from app.models import GenerateRequest, TaskStatus


@dataclass
class Task:
    task_id: str
    status: TaskStatus
    prompt: str
    width: int
    height: int
    guidance_scale: float
    num_inference_steps: int
    seed: Optional[int]
    progress: float = 0.0
    error: Optional[str] = None
    output_path: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


_registry: dict[str, Task] = {}
_pipeline: Optional[StableDiffusionPipeline] = None
_pipeline_lock = threading.Lock()
# Serialize generation so a single CPU/limited-VRAM GPU is never overloaded
_generation_lock = threading.Lock()


def _resolve_device() -> str:
    if DEVICE == "cpu":
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_pipeline() -> StableDiffusionPipeline:
    global _pipeline
    with _pipeline_lock:
        if _pipeline is not None:
            return _pipeline

        device = _resolve_device()
        dtype = torch.float16 if (USE_FLOAT16 and device == "cuda") else torch.float32

        pipe = StableDiffusionPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=dtype,
            safety_checker=None,
            requires_safety_checker=False,
        )

        if ENABLE_ATTENTION_SLICING:
            pipe.enable_attention_slicing()

        _pipeline = pipe.to(device)
        return _pipeline


def _run_generation(task: Task, request: GenerateRequest) -> None:
    with _generation_lock:
        task.status = TaskStatus.running
        task.progress = 0.0

        try:
            pipe = _load_pipeline()
            device = _resolve_device()

            generator = None
            if request.seed is not None:
                generator = torch.Generator(device=device).manual_seed(request.seed)

            total_steps = request.num_inference_steps

            def on_step_end(pipeline, step: int, timestep: int, callback_kwargs: dict):
                task.progress = (step + 1) / total_steps
                return callback_kwargs

            OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

            result = pipe(
                prompt=request.prompt,
                width=request.width,
                height=request.height,
                guidance_scale=request.guidance_scale,
                num_inference_steps=request.num_inference_steps,
                generator=generator,
                callback_on_step_end=on_step_end,
            )

            image = result.images[0]
            output_path = get_output_path(task.task_id)
            image.save(str(output_path), format="PNG")

            task.output_path = output_path
            task.status = TaskStatus.completed
            task.progress = 1.0

        except Exception as exc:
            task.status = TaskStatus.failed
            task.error = str(exc)
            task.progress = 0.0


def create_task(request: GenerateRequest) -> Task:
    task_id = str(uuid.uuid4())
    task = Task(
        task_id=task_id,
        status=TaskStatus.queued,
        prompt=request.prompt,
        width=request.width,
        height=request.height,
        guidance_scale=request.guidance_scale,
        num_inference_steps=request.num_inference_steps,
        seed=request.seed,
    )
    _registry[task_id] = task

    thread = threading.Thread(target=_run_generation, args=(task, request), daemon=True)
    thread.start()

    return task


def get_task(task_id: str) -> Optional[Task]:
    return _registry.get(task_id)


def get_output_path(task_id: str) -> Path:
    return OUTPUTS_DIR / f"{task_id}.png"


def cleanup_old_tasks(retention_hours: Optional[int] = None) -> int:
    """Delete output files and task records older than retention_hours. Returns count removed."""
    from app.config import RETENTION_HOURS
    hours = retention_hours if retention_hours is not None else RETENTION_HOURS
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    removed = 0
    for task_id in list(_registry.keys()):
        task = _registry[task_id]
        if task.created_at < cutoff:
            if task.output_path and task.output_path.exists():
                task.output_path.unlink(missing_ok=True)
            del _registry[task_id]
            removed += 1
    return removed
