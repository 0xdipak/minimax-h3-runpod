# linux/amd64 CUDA worker for MiniMax H3 on Runpod Serverless
FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/runpod-volume/huggingface-cache \
    TRANSFORMERS_CACHE=/runpod-volume/huggingface-cache \
    OUTPUT_DIR=/tmp/h3_outputs \
    H3_EAGER_LOAD=1 \
    H3_MEMORY_MODE=auto

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependency layer first for better cache reuse
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY cost.py upload.py upscale.py h3_pipeline.py handler.py /app/
COPY test_input.json /app/test_input.json

# Large model weights are NOT baked in — use Runpod cached models:
# Endpoint Model field: MiniMaxAI/MiniMax-H3
# Resolved at runtime via /runpod-volume/huggingface-cache/hub/...

RUN mkdir -p /tmp/h3_outputs

CMD ["python", "-u", "handler.py"]
