#!/bin/bash
set -e

# FFmpeg dev headers are required to build PyAV (faster-whisper dependency)
apt-get install -y ffmpeg libavformat-dev libavcodec-dev libavdevice-dev \
    libavutil-dev libavfilter-dev libswscale-dev libswresample-dev

pip install -r requirements.txt
