# Local AI Voice Generator - Implementation Tasks

## 1. Dependencies
- [x] Add `chatterbox-tts` and `whisperx` to `requirements.txt`
- [x] Create `outputs/voice/` subdirectory

## 2. Schemas
- [x] Create `app/voice_models.py` with:
  - `VoiceGenerateRequest` — `text: str` (max 500 chars), `language: str = "en"`
  - `VoiceTaskResponse` — `task_id`, `status`
  - `VoiceStatusResponse` — `task_id`, `status`, optional `timestamps` list, optional `error`
  - `WordTimestamp` — `word: str`, `start: float`, `end: float`

## 3. Voice Generator
- [x] Create `app/voice_generator.py` with:
  - Load Chatterbox TTS model once at startup (CPU default, GPU if CUDA available and VRAM safe)
  - `synthesize(text, output_path)` — run TTS, save WAV to `outputs/voice/<task_id>.wav`
  - `align(audio_path, text, language)` — run WhisperX with `compute_type="int8"`, `batch_size=4`, return word-level timestamp list
  - `run_voice_task(task_id, text, language)` — orchestrate synthesize → align → update task registry

## 4. Task Registry
- [x] Add a separate in-memory `voice_tasks` dict (same structure as image `tasks`: `status`, `error`, `timestamps`)
- [x] Add task status states: `queued`, `running`, `completed`, `failed`
- [x] Store word-level timestamps in the task record on completion

## 5. Background Queue
- [x] Add a sequential voice task queue (separate from the image queue)
- [x] Start the voice background worker thread at app startup alongside the image worker

## 6. API Endpoints
- [x] Add `POST /voice/generate` to `app/main.py`:
  - Validate request, enforce 500-char limit
  - Create voice task, enqueue it, return `task_id` and `status: queued`
  - Require Bearer token auth
- [x] Add `GET /voice/status/{task_id}` to `app/main.py`:
  - Return current status; include `timestamps` array when `completed`
  - Return 404 if task ID unknown
  - Require Bearer token auth
- [x] Add `GET /voice/download/{task_id}` to `app/main.py`:
  - Serve `outputs/voice/<task_id>.wav` as `audio/wav`
  - Return 404 if task not completed or file missing
  - Require Bearer token auth

## 7. Testing and Validation
- [ ] Test `POST /voice/generate` with a short English sentence
- [ ] Verify WAV file is saved to `outputs/voice/`
- [ ] Confirm `GET /voice/status/{task_id}` returns correct timestamps on completion
- [ ] Confirm `GET /voice/download/{task_id}` returns a playable WAV file
- [ ] Test 500-char limit enforcement (should return 422)
- [ ] Test auth rejection (missing/wrong token should return 401)
