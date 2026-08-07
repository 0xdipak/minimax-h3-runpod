# MiniMax H3 on Runpod Serverless

Smallest production-usable **Runpod Serverless Queue** worker for open-weight [MiniMax H3](https://huggingface.co/MiniMaxAI/MiniMax-H3).

Submit an ad-hoc prompt, get a durable MP4 URL (TikTok 1080×1920 by default), with **$/generated-second** instrumentation vs MiniMax’s hosted baseline (`$0.13/sec`).

## Architecture

- Python 3.10+ / `runpod` SDK / `handler.py`
- Official **diffusers ModularPipeline** `workflow="t2va"` (FL2VA text-to-video+audio)
- Model loaded **once per worker lifecycle** (eager load at process start)
- Flex workers, **scale-to-zero**, Queue endpoint
- Burst = many independent `/run` jobs sharing a warm worker (native queue)
- Outputs uploaded to S3-compatible storage (or local `file://` for tests)

```text
cold worker → init container → load H3 once → job1 → job2 → … → idle timeout → scale to zero
```

## Quick start (client)

```bash
cp .env.example .env
# fill RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID, optional S3_*, HF_TOKEN

python client.py --input test_input.json
# or
python client.py --prompt "..." --duration 10 --aspect-ratio 9:16 --quality draft
```

Expected CLI summary:

```text
H3 generation complete
Output: 10.1 sec
Resolution: 544x960 -> 1080x1920
GPU compute: 188.4 sec
Estimated Runpod cost: $0.091
Cost/output-sec: $0.0091
MiniMax equivalent: $1.31
Savings: 93.0%
```

Local handler smoke (needs a capable GPU + weights):

```bash
RUNPOD_LOCAL_TEST=1 H3_EAGER_LOAD=0 python client.py --local --input test_input.json
# or
python -u handler.py  # picks up test_input.json when RUNPOD_LOCAL_TEST patterns apply
```

## Request schema

```json
{
  "input": {
    "prompt": "...",
    "duration": 10,
    "aspect_ratio": "9:16",
    "seed": 123,
    "resolution_preset": "draft",
    "upscale": true
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `prompt` | yes | H3-style shot/audio description recommended |
| `duration` | no | 4–15s; snapped to H3 `17n+5` frames @ 24fps |
| `aspect_ratio` | no | `9:16` (default), `16:9`, `1:1` |
| `seed` | no | int |
| `resolution_preset` / `quality` | no | `draft` (544×960), `720p` (720×1280), `native` (768×1344) for 9:16 |
| `upscale` | no | default `true` → 1080×1920 for 9:16 |
| `num_inference_steps` | no | default `20` |
| `jobs` | no | optional list of the above; runs sequentially on one warm worker |

## Build & push worker image

Preferred production image (baked deps):

```bash
# amd64 (required for Runpod GPU hosts)
podman build --platform linux/amd64 -t ghcr.io/YOUR_USER/minimax-h3-runpod:latest .
podman push ghcr.io/YOUR_USER/minimax-h3-runpod:latest
# Make the GHCR package **public** (Package settings → Change visibility),
# or register GHCR credentials on the Runpod endpoint.
```

CI: `.github/workflows/build-push.yml` builds `ghcr.io/ruizmr/minimax-h3-runpod:latest`.

**Bootstrap deploy (no private registry):** use public `pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime` with `scripts/worker_entrypoint.sh` as the container start command (clones this repo, installs deps, runs `handler.py`). Slower cold starts; switch to the baked image once GHCR is public.

**Do not bake weights into the image.** Prefer Runpod **cached models** (`MiniMaxAI/MiniMax-H3`) so download time is not billed.

## Deployed endpoint (bootstrap)

| Field | Value |
|---|---|
| Endpoint ID | `obwhejrcoighto` |
| Type | Queue-based Flex |
| Image | `pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime` + `scripts/worker_entrypoint.sh` |
| GPU priority | L40S / RTX 6000 Ada / L40 → A100 |
| Active workers | 0 |
| Max workers | 2 |
| Idle timeout | 120s |
| Execution timeout | 3600s |
| FlashBoot | on |

```bash
export RUNPOD_ENDPOINT_ID=obwhejrcoighto
python client.py --input test_input.json
```

## Exact Runpod endpoint configuration

Console: [Serverless → New Endpoint → Docker](https://www.console.runpod.io/serverless)

| Field | Value |
|---|---|
| **Endpoint name** | `minimax-h3` (any) |
| **Endpoint type** | **Queue-based** |
| **Container image** | `YOUR_DOCKERHUB_USER/minimax-h3-runpod:latest` |
| **Container disk** | **50 GB** (encode temp + pip caches; models via HF cache volume) |
| **GPU** priority | **1)** L40 / L40S / 6000 Ada (48GB PRO) **2)** A100 (80GB) **3)** optional H100 |
| **GPUs per worker** | `1` |
| **Active workers** | `0` (Flex / scale-to-zero) |
| **Max workers** | `2` (raise for large bursts) |
| **Idle timeout** | **120 seconds** (critical for burst amortization; do **not** leave at 5s) |
| **Execution timeout** | **3600 seconds** |
| **FlashBoot** | **Enabled** |
| **Model (cached)** | `MiniMaxAI/MiniMax-H3` |
| **Auto-scaling type** | Queue delay, threshold ~4s |
| **Expose HTTP ports** | none (queue handler only) |

### Environment variables (endpoint)

Copy from `.env.example`. Minimum:

| Key | Example |
|---|---|
| `HF_TOKEN` | Hugging Face token (if needed for download/gated access) |
| `H3_MEMORY_MODE` | `auto` (or `int8_group_offload` / `a100_bf16_offload`) |
| `RUNPOD_GPU_TYPE` | `L40S` or `A100` (for cost math) |
| `RUNPOD_GPU_RATE_PER_SEC` | `0.00053` (L40S) or `0.00076` (A100) |
| `MINIMAX_RATE_PER_SEC` | `0.13` |
| `S3_BUCKET` / `S3_ENDPOINT_URL` / keys | durable outputs |
| `S3_PUBLIC_BASE_URL` | optional CDN base |
| `H3_EAGER_LOAD` | `1` |
| `H3_DEFAULT_PRESET` | `draft` for cheapest TikToks |

After deploy, set locally:

```bash
export RUNPOD_ENDPOINT_ID=xxxxxxxx
export RUNPOD_API_KEY=rpa_...
```

## Burst / warm-worker usage

Prefer **independent jobs** (native queue) over packing one giant request:

```bash
python burst.py --count 10 --quality draft --duration 10
```

With **Idle timeout = 120s**, a rapid burst typically:

1. Pays model load once (cold)
2. Serves remaining jobs warm
3. Scales to zero after the queue drains

Optional packed batch (same worker, sequential):

```json
{"input": {"jobs": [{"prompt": "...", "duration": 10}, {"prompt": "...", "duration": 8}]}}
```

## Benchmarks

```bash
python benchmark.py --duration 10
# writes docs/benchmark_results.md
```

Runs:

1. draft / 720p / native resolution matrix (same prompt)
2. cold then warm pair (waits for scale-to-zero)
3. 10-job burst economics

## Cost model

Estimate = `(model_init_if_cold + inference + upscale + upload) * RUNPOD_GPU_RATE_PER_SEC`

Savings vs MiniMax = `1 - cost_per_output_second / MINIMAX_RATE_PER_SEC`

Rates are env-configurable — never hard-code production pricing in call sites.

## Memory modes

| Mode | GPU | Notes |
|---|---|---|
| `a100_bf16_offload` | ≥70GB VRAM (A100) | Official ComponentsManager BF16 offload |
| `int8_group_offload` | 48GB class | Official torchao int8 + group offload; needs ample host RAM (~75GB+ ideal → prefer L40S/6000 Ada over A40) |
| `auto` | detects VRAM | chooses between the two |

## Repo layout

```text
handler.py          Runpod entry
h3_pipeline.py      load-once ModularPipeline
cost.py             $/sec math
upload.py           S3-compatible upload
upscale.py          → 1080×1920 + audio
client.py           single job CLI
burst.py            N independent jobs
benchmark.py        economics suite
Dockerfile
requirements.txt
test_input.json
.env.example
docs/benchmark_results.md
```

## Notes / limits

- Official **H3-Regenerate-2K is not open-sourced**; 1080×1920 is native 9:16 + high-quality upscale (ffmpeg lanczos by default).
- H3 emits **native stereo audio** in one pass.
- Payload limits mean videos are **not** returned inline — always upload (or local file URL).
- Never commit `.env` or credentials.

## License

Model weights are under the [MiniMax H3 Community License](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE). This worker code is provided as-is for deployment experiments.
