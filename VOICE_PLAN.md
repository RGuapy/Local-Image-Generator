# Local AI Voice Generator Plan

## Goal
Extend the existing FastAPI service with a voice generation feature that accepts a short text input, synthesizes speech using Chatterbox TTS, and returns both the audio file and word-level timestamps (via WhisperX) suitable for subtitle synchronization.

## Requirements
- New endpoints under `/voice/` mirroring the existing image generator pattern
- Text-to-speech synthesis using [Chatterbox TTS](https://github.com/resemble-ai/chatterbox)
- Word-level timestamp alignment using WhisperX
- Return audio as a downloadable WAV file
- Return timestamps as a JSON array with `word`, `start`, and `end` fields
- Local execution on CPU by default; GPU fallback with careful VRAM management
- Reuse the existing task lifecycle, auth, and queue infrastructure

## Machine Profile (same as image generator)
- CPU: AMD Ryzen 5 3600 (6-core)
- RAM: 32 GiB
- GPU: NVIDIA GeForce GTX 650 Ti (limited VRAM — ~2 GiB)

## API Contract

### `POST /voice/generate`
Request body:
```json
{
  "text": "Short text to synthesize.",
  "language": "en"
}
```
Response:
```json
{
  "task_id": "abc123",
  "status": "queued"
}
```

### `GET /voice/status/{task_id}`
Response while processing:
```json
{
  "task_id": "abc123",
  "status": "running"
}
```
Response when complete (timestamps embedded here — small payload):
```json
{
  "task_id": "abc123",
  "status": "completed",
  "timestamps": [
    { "word": "Short", "start": 0.1, "end": 0.4 },
    { "word": "text", "start": 0.45, "end": 0.7 }
  ]
}
```
Response on failure:
```json
{
  "task_id": "abc123",
  "status": "failed",
  "error": "description of the error"
}
```

### `GET /voice/download/{task_id}`
- Returns the generated WAV audio file as a binary download (`audio/wav`)
- Returns 404 if task is not completed or file is missing

## Generation Workflow

1. Accept `POST /voice/generate`, create a task, push to the voice queue
2. Background worker picks up the task
3. Chatterbox TTS synthesizes speech from `text`, saves to `outputs/voice/<task_id>.wav`
4. WhisperX aligns the audio to extract word-level timestamps
5. Timestamps are stored in-memory alongside the task record
6. Task status is set to `completed`; audio file remains on disk
7. Client polls `GET /voice/status/{task_id}` to get timestamps, then fetches audio via `GET /voice/download/{task_id}`

## Local Execution Strategy

### Chatterbox TTS
- Load model once at startup (same pattern as the SD pipeline)
- Default to CPU; enable GPU only if CUDA is available and VRAM allows
- Use `torch.float16` on GPU, `torch.float32` on CPU
- GTX 650 Ti has ~2 GiB VRAM — test carefully; fall back to CPU if OOM

### WhisperX
- Run `whisperx` with `compute_type="int8"` on CPU for low memory use
- Use `batch_size=4` or lower to stay within RAM limits
- Run alignment pass (`whisperx.align`) to obtain word-level segments
- Language defaults to `"en"`; caller can override via the `language` field

## Storage and File Management
- Audio outputs: `outputs/voice/<task_id>.wav`
- Timestamps: stored in-memory task registry (same `tasks` dict as image tasks, keyed with a `voice_` prefix or separate registry)
- Reuse the existing cleanup / retention policy from the image generator

## Project Structure (additions only)
- `app/voice_generator.py` — Chatterbox TTS synthesis + WhisperX alignment logic
- `app/voice_models.py` — Pydantic request/response schemas for voice endpoints
- `app/main.py` — add `/voice/*` routes (extend existing file)
- `outputs/voice/` — generated WAV files

## Dependencies to Add to `requirements.txt`
```
chatterbox-tts
whisperx
```
> Note: `whisperx` depends on `faster-whisper`, `torch`, `torchaudio`, and `ffmpeg` being available on the system path. `torch` is already present.

## Timestamp Output Format
Word-level timestamps returned by WhisperX and stored in the task record:
```json
[
  { "word": "Mas", "start": 0.1, "end": 0.325 },
  { "word": "o",   "start": 0.338, "end": 0.463 }
]
```

## Constraints and Notes
- Keep the voice queue sequential (one task at a time) to avoid memory contention with the image generator queue
- Do not load both the SD pipeline and Chatterbox model simultaneously if GPU is in use — risk of OOM on GTX 650 Ti
- Chatterbox and WhisperX models should be downloaded once and cached locally (respect `HF_HOME` / model cache dir)
- Auth: all `/voice/*` endpoints must enforce the same `Authorization: Bearer <token>` check as image endpoints
- Maximum input text length: 500 characters (enforce at schema level to keep synthesis fast and output small)

## Next Files to Create
- `app/voice_models.py`
- `app/voice_generator.py`
- Update `app/main.py` with `/voice/*` routes
- Update `requirements.txt` with new dependencies
- Update `outputs/` to include `voice/` subdirectory
