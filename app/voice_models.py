from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class VoiceGenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    language: Literal["en", "pt"] = "en"


class VoiceTaskResponse(BaseModel):
    task_id: str
    status: str


class VoiceStatusResponse(BaseModel):
    task_id: str
    status: str
    error: Optional[str] = None
