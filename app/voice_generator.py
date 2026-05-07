import queue
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import torch
import torchaudio

from app.config import DEVICE, OUTPUTS_DIR
from app.voice_models import WordTimestamp

VOICE_OUTPUTS_DIR = OUTPUTS_DIR / "voice"
CHATTERBOX_SAMPLE_RATE = 24000
VOICE_FORMAT = "mp3"

_tts_model = None
_tts_lock = threading.Lock()
_voice_queue: queue.Queue = queue.Queue()


@dataclass
class VoiceTask:
    task_id: str
    status: str  # queued | running | completed | failed
    text: str
    language: str
    error: Optional[str] = None
    timestamps: Optional[List[WordTimestamp]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


_voice_tasks: dict[str, VoiceTask] = {}


def _resolve_device() -> str:
    if DEVICE == "cpu":
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_tts_model():
    global _tts_model
    with _tts_lock:
        if _tts_model is not None:
            return _tts_model
        from chatterbox.tts import ChatterboxTTS
        device = _resolve_device()
        if device == "cpu":
            # Chatterbox checkpoints may be saved on CUDA; force CPU deserialization
            _orig_load = torch.load
            def _cpu_load(*args, **kwargs):
                kwargs.setdefault("map_location", "cpu")
                return _orig_load(*args, **kwargs)
            torch.load = _cpu_load
            try:
                _tts_model = ChatterboxTTS.from_pretrained(device=device)
            finally:
                torch.load = _orig_load
        else:
            _tts_model = ChatterboxTTS.from_pretrained(device=device)
        return _tts_model


def synthesize(text: str, output_path: Path) -> None:
    model = _load_tts_model()
    wav = model.generate(text)
    VOICE_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    torchaudio.save(str(output_path), wav.cpu(), CHATTERBOX_SAMPLE_RATE, format=VOICE_FORMAT)


def align(audio_path: Path, text: str, language: str) -> List[WordTimestamp]:
    from faster_whisper import WhisperModel
    device = _resolve_device()
    model = WhisperModel("base", device=device, compute_type="int8")
    segments, _ = model.transcribe(str(audio_path), word_timestamps=True, language=language)
    words = []
    for segment in segments:
        for word in (segment.words or []):
            words.append(WordTimestamp(word=word.word.strip(), start=word.start, end=word.end))
    return words


def run_voice_task(task_id: str, text: str, language: str) -> None:
    task = _voice_tasks.get(task_id)
    if task is None:
        return

    task.status = "running"
    try:
        output_path = get_voice_output_path(task_id)
        synthesize(text, output_path)
        task.timestamps = align(output_path, text, language)
        task.status = "completed"
    except Exception as exc:
        task.status = "failed"
        task.error = str(exc)


def _voice_worker() -> None:
    while True:
        task_id, text, language = _voice_queue.get()
        try:
            run_voice_task(task_id, text, language)
        finally:
            _voice_queue.task_done()


def start_voice_worker() -> None:
    thread = threading.Thread(target=_voice_worker, daemon=True)
    thread.start()


def create_voice_task(text: str, language: str) -> VoiceTask:
    task_id = str(uuid.uuid4())
    task = VoiceTask(task_id=task_id, status="queued", text=text, language=language)
    _voice_tasks[task_id] = task
    _voice_queue.put((task_id, text, language))
    return task


def get_voice_task(task_id: str) -> Optional[VoiceTask]:
    return _voice_tasks.get(task_id)


def get_voice_output_path(task_id: str) -> Path:
    return VOICE_OUTPUTS_DIR / f"{task_id}.{VOICE_FORMAT}"


def cleanup_old_voice_tasks(retention_hours: Optional[int] = None) -> int:
    from app.config import RETENTION_HOURS
    hours = retention_hours if retention_hours is not None else RETENTION_HOURS
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    removed = 0
    for task_id in list(_voice_tasks.keys()):
        task = _voice_tasks[task_id]
        if task.created_at < cutoff:
            output_path = get_voice_output_path(task_id)
            output_path.unlink(missing_ok=True)
            del _voice_tasks[task_id]
            removed += 1
    return removed
