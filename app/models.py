from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.config import (
    DEFAULT_GUIDANCE_SCALE,
    DEFAULT_HEIGHT,
    DEFAULT_NUM_INFERENCE_STEPS,
    DEFAULT_WIDTH,
)


class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class GenerateRequest(BaseModel):
    prompt: str
    width: Optional[int] = Field(default=DEFAULT_WIDTH, ge=64, le=2048)
    height: Optional[int] = Field(default=DEFAULT_HEIGHT, ge=64, le=2048)
    guidance_scale: Optional[float] = Field(default=DEFAULT_GUIDANCE_SCALE, ge=1.0, le=30.0)
    num_inference_steps: Optional[int] = Field(default=DEFAULT_NUM_INFERENCE_STEPS, ge=1, le=200)
    seed: Optional[int] = None


class GenerateResponse(BaseModel):
    task_id: str
    status: TaskStatus


class StatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: Optional[float] = None
    error: Optional[str] = None
