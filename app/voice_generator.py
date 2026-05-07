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
_fish_queue = None
_fish_tokenizer = None
_fish_decoder = None
_fish_lock = threading.Lock()
_voice_queue: queue.Queue = queue.Queue()

FISH_SAMPLE_RATE = 44100


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


def _load_fish_speech_models():
    global _fish_queue, _fish_tokenizer, _fish_decoder
    with _fish_lock:
        if _fish_queue is not None:
            return _fish_queue, _fish_tokenizer, _fish_decoder
        import torch
        from pathlib import Path as _Path
        from huggingface_hub import snapshot_download
        from fish_speech.models.text2semantic.inference import launch_thread_safe_queue
        from fish_speech.models.vqgan.inference import load_model as load_decoder
        device = _resolve_device()
        precision = torch.float16 if device == "cuda" else torch.float32
        repo_dir = _Path(snapshot_download("fishaudio/fish-speech-1.5"))
        _fish_queue, _fish_tokenizer, _ = launch_thread_safe_queue(
            checkpoint_path=repo_dir,
            device=device,
            precision=precision,
            compile=False,
        )
        _fish_decoder = load_decoder(
            config_name="firefly_gan_vq",
            checkpoint_path=repo_dir,
            device=device,
            precision=precision,
        )
        return _fish_queue, _fish_tokenizer, _fish_decoder


def _synthesize_fish_speech(text: str, output_path: Path, exaggeration: float) -> None:
    import numpy as np
    from fish_speech.models.text2semantic.inference import InferenceRequest, GenerateResponse
    from fish_speech.models.vqgan.inference import decode_vq_tokens
    llm_queue, tokenizer, decoder = _load_fish_speech_models()
    # Map exaggeration to LLM temperature: 0.0 → 0.5 (calm), 1.5 → 1.25 (very expressive)
    temperature = 0.5 + exaggeration * 0.5
    request = InferenceRequest(
        device=_resolve_device(),
        max_new_tokens=1024,
        text=[text],
        top_p=0.7,
        repetition_penalty=1.3,
        temperature=temperature,
    )
    llm_queue.put(request)
    segments = []
    while True:
        wrapped = request.response_queue.get()
        if wrapped is None:
            break
        if wrapped == "error" or (hasattr(wrapped, "status") and wrapped.status == "error"):
            raise RuntimeError(f"Fish Speech LLM error: {getattr(wrapped, 'response', wrapped)}")
        resp = wrapped.response if hasattr(wrapped, "response") else wrapped
        if isinstance(resp, GenerateResponse):
            chunk = decode_vq_tokens(
                model=decoder,
                codes=resp.codes.squeeze(0).T.tolist(),
            )
            segments.append(chunk)
    if not segments:
        raise RuntimeError("Fish Speech returned no audio segments")
    audio = np.concatenate(segments)
    audio_tensor = torch.from_numpy(audio).unsqueeze(0)
    torchaudio.save(str(output_path), audio_tensor, FISH_SAMPLE_RATE, format=VOICE_FORMAT)


def synthesize(text: str, output_path: Path, language: str = "en", exaggeration: float = 0.8) -> None:
    VOICE_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    if language == "pt":
        _synthesize_fish_speech(text, output_path, exaggeration)
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
