import os
from pathlib import Path

# Output directory for generated images
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", "outputs"))

# Default Stable Diffusion model from Hugging Face
MODEL_ID = os.getenv("MODEL_ID", "runwayml/stable-diffusion-v1-5")

# Default 9:16 portrait image dimensions
DEFAULT_WIDTH = int(os.getenv("DEFAULT_WIDTH", "512"))
DEFAULT_HEIGHT = int(os.getenv("DEFAULT_HEIGHT", "896"))

# Generation defaults
DEFAULT_GUIDANCE_SCALE = float(os.getenv("DEFAULT_GUIDANCE_SCALE", "9.0"))
DEFAULT_NUM_INFERENCE_STEPS = int(os.getenv("DEFAULT_NUM_INFERENCE_STEPS", "50"))

# Hardware — prefer CPU; enable GPU only when CUDA is available and VRAM permits
DEVICE = os.getenv("DEVICE", "cpu")
USE_FLOAT16 = os.getenv("USE_FLOAT16", "false").lower() == "true"
ENABLE_ATTENTION_SLICING = os.getenv("ENABLE_ATTENTION_SLICING", "true").lower() == "true"

# Retention policy — files and task records older than this are eligible for cleanup
RETENTION_HOURS = int(os.getenv("RETENTION_HOURS", "24"))
# How often the background cleanup thread runs (seconds)
CLEANUP_INTERVAL_SECONDS = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "3600"))

# Token file — must exist on the server before startup; contains the raw secret token
TOKEN_FILE = Path(os.getenv("TOKEN_FILE", "api_token.txt"))
