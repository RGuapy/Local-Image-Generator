# Local AI Image Renderer - Implementation Tasks

## 1. Project Setup
- [x] Create Python virtual environment
- [x] Add `requirements.txt` with FastAPI, Uvicorn, diffusers, transformers, torch, pydantic
- [x] Create basic project directory structure: `app/`, `outputs/`

## 2. API Scaffolding
- [x] Create `app/main.py` with FastAPI application instance
- [x] Implement endpoints:
  - `POST /generate`
  - `GET /status/{task_id}`
  - `GET /download/{task_id}`
- [x] Add CORS middleware if needed for local frontends

## 3. Schemas and Config
- [x] Create `app/models.py` for request/response Pydantic models
- [x] Add `app/config.py` for default settings and environment values
- [x] Define default 9:16 target size and generation options

## 4. Task Management
- [x] Implement task lifecycle and in-memory task registry
- [x] Add task status states: queued, running, completed, failed
- [x] Create unique task IDs and local image file naming
- [x] Add progress tracking and error message storage

## 5. Diffusers Integration
- [x] Create `app/generator.py` with Stable Diffusion generation logic
- [x] Load model with CPU as default and GPU fallback if CUDA is available
- [x] Use memory-efficient config and low VRAM settings for GTX 650 Ti
- [x] Support portrait 9:16 sizes like `512x896` and `640x1024`
- [x] Save outputs as PNG files in `outputs/`

## 6. Background Execution
- [x] Run generation in background worker or thread from FastAPI endpoint
- [x] Ensure API responds immediately with task ID
- [x] Maintain safe single-task queue or sequential execution for local hardware

## 7. Download and Cleanup
- [x] Add `GET /download/{task_id}` to serve completed image files
- [x] Implement failure handling for missing or incomplete outputs
- [x] Add optional retention policy or cleanup script for old files

## 8. Testing and Local Validation
- [ ] Test sample `POST /generate` requests using `curl` or HTTP client
- [ ] Validate 9:16 image output and file save path
- [ ] Verify status polling and successful download flow

## 10. Quality Improvements
- [x] Add `negative_prompt` field to `GenerateRequest` and wire it through to the pipeline
- [x] Detect CLIP token overflow (>77 tokens) and surface `prompt_truncated` warning in `StatusResponse`
- [x] Update default `guidance_scale` from 7.5 to 9.0 for better style adherence

## 9. Security
- [x] Add token file auth: server reads `api_token.txt` at startup, all endpoints require `Authorization: Bearer <token>`
- [x] Server refuses to start if token file is missing or empty

## 11. Documentation
- [ ] Create `README.md` with setup instructions, API examples, and usage notes
- [ ] Document local performance expectations and GPU limitations
- [ ] Add model selection and default image resolution guidance
