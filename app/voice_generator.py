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
VOICE_FORMAT = "wav"

_tts_model = None
_tts_lock = threading.Lock()
_mms_pt_model = None
_mms_pt_tokenizer = None
_mms_pt_lock = threading.Lock()
_voice_queue: queue.Queue = queue.Queue()


@dataclass
class VoiceTask:
    task_id: str
    status: str  # queued | running | completed | failed
    text: str
    language: str
    exaggeration: float = 0.8
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


def _load_mms_pt_model():
    global _mms_pt_model, _mms_pt_tokenizer
    with _mms_pt_lock:
        if _mms_pt_model is not None:
            return _mms_pt_model, _mms_pt_tokenizer
        from transformers import AutoTokenizer, VitsModel
        _mms_pt_tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-por")
        _mms_pt_model = VitsModel.from_pretrained("facebook/mms-tts-por")
        _mms_pt_model.eval()
        return _mms_pt_model, _mms_pt_tokenizer


def synthesize(text: str, output_path: Path, language: str = "en", exaggeration: float = 0.8) -> None:
    VOICE_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    if language == "pt":
        model, tokenizer = _load_mms_pt_model()
        inputs = tokenizer(text, return_tensors="pt")
        # MMS has no emotion model; map exaggeration linearly to speaking_rate as a proxy
        speaking_rate = 0.85 + exaggeration * 0.43
        with torch.no_grad():
            wav = model(**inputs, speaking_rate=speaking_rate).waveform
        torchaudio.save(str(output_path), wav.cpu(), model.config.sampling_rate, format=VOICE_FORMAT)
    else:
        model = _load_tts_model()
        wav = model.generate(text, exaggeration=exaggeration)
        torchaudio.save(str(output_path), wav.cpu(), CHATTERBOX_SAMPLE_RATE, format=VOICE_FORMAT)


def align(audio_path: Path, text: str, language: str) -> List[WordTimestamp]:
    from transformers import pipeline as hf_pipeline
    device = _resolve_device()

    waveform, sample_rate = torchaudio.load(str(audio_path))
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    if sample_rate != 16000:
        waveform = torchaudio.transforms.Resample(sample_rate, 16000)(waveform)
    audio_array = waveform.squeeze().numpy().astype("float32")

    asr = hf_pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-base",
        device=0 if device == "cuda" else -1,
        return_timestamps="word",
    )
    result = asr({"raw": audio_array, "sampling_rate": 16000}, generate_kwargs={"language": language})

    words = []
    for chunk in result.get("chunks") or []:
        ts = chunk.get("timestamp")
        if ts and len(ts) == 2:
            start, end = ts
            words.append(WordTimestamp(
                word=chunk["text"].strip(),
                start=float(start or 0.0),
                end=float(end or 0.0),
            ))
    return words


def run_voice_task(task_id: str, text: str, language: str, exaggeration: float) -> None:
    task = _voice_tasks.get(task_id)
    if task is None:
        return

    task.status = "running"
    try:
        output_path = get_voice_output_path(task_id)
        synthesize(text, output_path, language, exaggeration)
        task.timestamps = align(output_path, text, language)
        task.status = "completed"
    except Exception as exc:
        task.status = "failed"
        task.error = str(exc)


def _voice_worker() -> None:
    while True:
        task_id, text, language, exaggeration = _voice_queue.get()
        try:
            run_voice_task(task_id, text, language, exaggeration)
        finally:
            _voice_queue.task_done()


def start_voice_worker() -> None:
    thread = threading.Thread(target=_voice_worker, daemon=True)
    thread.start()


def create_voice_task(text: str, language: str, exaggeration: float = 0.8) -> VoiceTask:
    task_id = str(uuid.uuid4())
    task = VoiceTask(task_id=task_id, status="queued", text=text, language=language, exaggeration=exaggeration)
    _voice_tasks[task_id] = task
    _voice_queue.put((task_id, text, language, exaggeration))
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
