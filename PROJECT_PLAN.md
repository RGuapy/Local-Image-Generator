# Local AI Image Renderer Project Plan

## Goal
Build a local image generation service using Stable Diffusion and FastAPI that can receive requests to start rendering images and provide a download endpoint once rendering completes.

## Requirements
- API backend using FastAPI
- Image generation using Hugging Face `diffusers` with Stable Diffusion
- Local execution on CPU or a limited GPU
- Optimized for quality over speed
- Support request/response flow for starting generation and downloading completed images
- Minimal external dependencies and no cloud-only components

## Machine Profile
- CPU: AMD Ryzen 5 3600 (6-core)
- RAM: 32 GiB
- GPU: NVIDIA GeForce GTX 650 Ti (limited VRAM)

## Design Overview

### 1. API Contract
- `POST /generate`
  - Request: JSON with prompt, optional image width/height, guidance scale, steps, seed, etc.
  - Response: task ID and status
- `GET /status/{task_id}`
  - Response: current task status, progress, error messages
- `GET /download/{task_id}`
  - Response: completed image file or download link

### 2. Generation Workflow
- Accept requests and create a new generation task
- Queue tasks for sequential or batched execution
- Run Stable Diffusion locally
- Save results to a local storage folder
- Return a task identifier immediately while processing continues

### 3. Local Execution Strategy
- Prefer CPU execution by default because GPU is limited
- Use performance tuning for low VRAM models:
  - Use `torch.float16` if available
  - Use reduced precision and memory-efficient attention
  - Target 9:16 portrait image sizes such as 512x896 or 640x1024
- Allow a limited GPU fallback if the environment supports CUDA and memory permits
- Keep model and scheduler loading efficient to avoid repeated warm-up

### 4. Storage and File Management
- Store generated images in a local `outputs/` directory
- Use unique task IDs and filenames
- Clean up old images after a configurable retention period
- Expose downloads through the API

### 5. Project Structure
- `app/main.py` — FastAPI app and endpoints
- `app/generator.py` — image generation logic and task management
- `app/models.py` — request/response schemas
- `app/config.py` — configuration values and environment settings
- `outputs/` — generated image files
- `requirements.txt` — project dependencies
- `PROJECT_PLAN.md` — project plan

## Implementation Steps

1. Initialize Python project
   - Create virtual environment
   - Install FastAPI, Uvicorn, `diffusers`, `transformers`, `torch`, `pydantic`
2. Build API scaffolding
   - Configure FastAPI app and endpoints
   - Create request/response models
3. Implement task lifecycle
   - Task creation, status tracking, result storage
   - In-memory queue or simple background worker
4. Integrate Stable Diffusion
   - Load a local Stable Diffusion model using `diffusers`
   - Add CPU/GPU fallback logic
   - Generate images and save PNG files
5. Add download endpoint
   - Serve completed image files securely
6. Test locally
   - Verify prompt generation with sample requests
   - Confirm download flow and status updates
7. Document usage
   - Add README with setup, API examples, and performance notes

## Notes and Constraints
- The NVIDIA GTX 650 Ti likely has limited VRAM; GPU usage may require small images and reduced batch sizes.
- CPU-only execution is safer on this machine, but it will be slower.
- Focus on quality by choosing stable model settings and using guidance scale and sufficient diffusion steps.
- Keep the API simple for local development.

## Next Files to Create
- `requirements.txt`
- `app/main.py`
- `app/generator.py`
- `app/models.py`
- `app/config.py`
- `README.md`
