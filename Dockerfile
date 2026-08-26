# linux/amd64 CUDA worker for MiniMax H3 on Runpod Serverless
FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime

# HF cache prefers a network volume when mounted; handler/entrypoint can override.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/h3-data/huggingface-cache \
    HUGGINGFACE_HUB_CACHE=/opt/h3-data/huggingface-cache \
    OUTPUT_DIR=/tmp/h3_outputs \
    H3_EAGER_LOAD=1 \
    H3_MEMORY_MODE=auto

# build-essential: triton JIT (pulled in via torchao/transformers) needs a C compiler at import/runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
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

# Forced, isolated install: a combined resolve of this git ref alongside
# transformers==5.14.1 (pinned above) was silently landing an older diffusers
# with no ModularPipeline at runtime. --no-deps keeps it from touching the
# already-resolved deps above; --force-reinstall guarantees it actually wins.
RUN pip install --no-cache-dir --force-reinstall --no-deps \
    "diffusers @ git+https://github.com/huggingface/diffusers.git@9c6a68c32b3b2a64db91800b624d33cec6e25ab8"

COPY cost.py upload.py upscale.py h3_pipeline.py handler.py /app/
COPY test_input.json /app/test_input.json

# Large model weights are NOT baked in — use Runpod cached models:
# Endpoint Model field: MiniMaxAI/MiniMax-H3
# Resolved at runtime via /runpod-volume/huggingface-cache/hub/...

RUN mkdir -p /tmp/h3_outputs /opt/h3-data/huggingface-cache

CMD ["python", "-u", "handler.py"]
