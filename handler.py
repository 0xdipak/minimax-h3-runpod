"""Runpod Serverless handler for MiniMax H3 ref2va (reference-image-guided video+audio)."""

from __future__ import annotations

import os
import time
import traceback
from pathlib import Path
from typing import Any

import runpod

from cost import compute_cost, format_cli_summary
from h3_pipeline import (
    MODEL_INIT_SECONDS,
    MODEL_LOADED,
    PipelineError,
    detect_gpu_name,
    generate,
    load_pipeline,
)
from upload import UploadError, upload_video
from upscale import UpscaleError, upscale_to_tiktok

# Reduce CUDA allocator fragmentation during large component swaps.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


# Worker-process cold flag: True until first successful model load completes.
_WORKER_STARTED_AT = time.perf_counter()
_FIRST_REQUEST = True
_MODEL_INIT_AT_LOAD = 0.0


def _configure_hf_cache() -> None:
    """Prefer network volume cache; fall back to local container disk."""
    for candidate in (
        "/runpod-volume/huggingface-cache",
        "/opt/h3-data/huggingface-cache",
        os.environ.get("HF_HOME") or "",
    ):
        if not candidate:
            continue
        root = Path(candidate)
        try:
            root.mkdir(parents=True, exist_ok=True)
            probe = root / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            os.environ["HF_HOME"] = str(root)
            os.environ["HUGGINGFACE_HUB_CACHE"] = str(root)
            os.environ["TRANSFORMERS_CACHE"] = str(root)
            print(f"[handler] HF cache -> {root}", flush=True)
            return
        except OSError as exc:
            print(f"[handler] HF cache unusable at {root}: {exc}", flush=True)


_configure_hf_cache()


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _validate_and_normalize(job_input: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(job_input, dict):
        raise ValueError("input must be a JSON object")

    # Optional packed batch: run sequentially on this warm worker.
    if "jobs" in job_input:
        jobs = job_input["jobs"]
        if not isinstance(jobs, list) or not jobs:
            raise ValueError("jobs must be a non-empty list")
        return [_normalize_one(j, index=i) for i, j in enumerate(jobs)]

    return [_normalize_one(job_input)]


def _normalize_one(raw: dict[str, Any], index: int | None = None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"job{'' if index is None else f'[{index}]'} must be an object")

    prompt = raw.get("prompt")
    if not prompt or not str(prompt).strip():
        raise ValueError("prompt is required and must be a non-empty string")

    reference_image_url = raw.get("reference_image_url")
    if not reference_image_url or not str(reference_image_url).strip():
        raise ValueError(
            "reference_image_url is required and must be a non-empty string (this worker only runs ref2va)"
        )

    duration = float(raw.get("duration", 10))
    if duration < 4 or duration > 15:
        raise ValueError("duration must be between 4 and 15 seconds")

    aspect_ratio = str(raw.get("aspect_ratio", "9:16"))
    preset = str(
        raw.get("resolution_preset")
        or raw.get("quality")
        or os.environ.get("H3_DEFAULT_PRESET", "native")
    )
    seed = raw.get("seed")
    if seed is not None:
        seed = int(seed)

    steps = raw.get("num_inference_steps")
    if steps is not None:
        steps = int(steps)
        if steps < 4 or steps > 50:
            raise ValueError("num_inference_steps must be between 4 and 50")

    return {
        "prompt": str(prompt).strip(),
        "reference_image_url": str(reference_image_url).strip(),
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution_preset": preset,
        "seed": seed,
        "num_inference_steps": steps,
        "upscale": _as_bool(raw.get("upscale"), True),
    }


def _run_one(spec: dict[str, Any], *, worker_cold: bool, model_init_seconds: float) -> dict[str, Any]:
    t_total0 = time.perf_counter()
    gpu_name = detect_gpu_name()

    gen = generate(
        prompt=spec["prompt"],
        reference_image_url=spec["reference_image_url"],
        duration=spec["duration"],
        aspect_ratio=spec["aspect_ratio"],
        resolution_preset=spec["resolution_preset"],
        seed=spec["seed"],
        num_inference_steps=spec["num_inference_steps"],
    )

    native_w, native_h = gen.width, gen.height
    out_path = gen.video_path
    out_w, out_h = native_w, native_h
    upscale_seconds = 0.0

    if spec["upscale"] and spec["aspect_ratio"] == "9:16":
        t_up = time.perf_counter()
        out_path = upscale_to_tiktok(gen.video_path)
        upscale_seconds = time.perf_counter() - t_up
        out_w, out_h = 1080, 1920
    elif spec["upscale"]:
        # Keep aspect; scale short side toward 1080-class when requested.
        t_up = time.perf_counter()
        if native_w >= native_h:
            out_w, out_h = 1920, 1080
        else:
            out_w, out_h = 1080, 1920
        out_path = upscale_to_tiktok(gen.video_path, width=out_w, height=out_h)
        upscale_seconds = time.perf_counter() - t_up

    t_upl = time.perf_counter()
    uploaded = upload_video(out_path)
    upload_seconds = time.perf_counter() - t_upl

    total_worker_seconds = time.perf_counter() - t_total0
    # Attribute model init only on the cold first request of this worker.
    billed = total_worker_seconds + (model_init_seconds if worker_cold else 0.0)

    cost = compute_cost(
        billed_seconds=billed,
        output_seconds=gen.duration,
        gpu_type=os.environ.get("RUNPOD_GPU_TYPE") or gpu_name,
    )

    summary = format_cli_summary(
        output_seconds=gen.duration,
        native_w=native_w,
        native_h=native_h,
        out_w=out_w,
        out_h=out_h,
        gpu_compute_seconds=billed,
        cost=cost,
    )
    print(summary)

    return {
        "video_url": uploaded["video_url"],
        "duration": gen.duration,
        "width": out_w,
        "height": out_h,
        "native_width": native_w,
        "native_height": native_h,
        "seed": gen.seed,
        "num_frames": gen.num_frames,
        "num_inference_steps": gen.num_inference_steps,
        "generation_seconds": round(gen.inference_seconds, 3),
        "timing": {
            "worker_cold": worker_cold,
            "model_init_seconds": round(model_init_seconds if worker_cold else 0.0, 3),
            "inference_seconds": round(gen.inference_seconds, 3),
            "upscale_seconds": round(upscale_seconds, 3),
            "upload_seconds": round(upload_seconds, 3),
            "total_worker_seconds": round(total_worker_seconds, 3),
            "billed_seconds_estimate": round(billed, 3),
            "worker_uptime_at_start": round(time.perf_counter() - _WORKER_STARTED_AT, 3),
        },
        "cost": cost,
        "storage": {k: v for k, v in uploaded.items() if k != "video_url"},
        "cli_summary": summary,
    }


def _debug_env() -> dict[str, Any]:
    """One-off diagnostic path — bypasses generation entirely. Not part of
    the real API; temporary aid for tracking down a diffusers import bug."""
    info: dict[str, Any] = {}

    try:
        import importlib.metadata as importlib_metadata

        for pkg in ("torch", "diffusers", "transformers", "accelerate", "torchao"):
            try:
                info[f"{pkg}_version"] = importlib_metadata.version(pkg)
            except Exception as exc:  # noqa: BLE001
                info[f"{pkg}_version"] = f"ERROR: {exc}"
    except Exception as exc:  # noqa: BLE001
        info["importlib_metadata_error"] = str(exc)

    try:
        import torch

        info["torch_import_ok"] = True
        info["torch___version__"] = torch.__version__
        info["torch___file__"] = torch.__file__
        info["torch_cuda_available"] = torch.cuda.is_available()
    except Exception as exc:  # noqa: BLE001
        info["torch_import_ok"] = False
        info["torch_import_error"] = f"{type(exc).__name__}: {exc}"

    try:
        import diffusers

        info["diffusers_import_ok"] = True
        info["diffusers___version__"] = getattr(diffusers, "__version__", "unknown")
        info["diffusers___file__"] = diffusers.__file__
        info["diffusers_dir_has_ModularPipeline"] = "ModularPipeline" in dir(diffusers)
    except Exception as exc:  # noqa: BLE001
        info["diffusers_import_ok"] = False
        info["diffusers_import_error"] = f"{type(exc).__name__}: {exc}"

    try:
        from diffusers.utils import import_utils as diffusers_import_utils

        info["diffusers_is_torch_available"] = diffusers_import_utils.is_torch_available()
        info["diffusers_is_transformers_available"] = diffusers_import_utils.is_transformers_available()
        info["USE_TORCH_env"] = os.environ.get("USE_TORCH", "<unset>")
        info["USE_TF_env"] = os.environ.get("USE_TF", "<unset>")
    except Exception as exc:  # noqa: BLE001
        info["diffusers_import_utils_error"] = f"{type(exc).__name__}: {exc}"

    try:
        import subprocess

        result = subprocess.run(
            ["pip", "show", "torch", "diffusers"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        info["pip_show_torch_diffusers"] = result.stdout
        info["pip_show_stderr"] = result.stderr
    except Exception as exc:  # noqa: BLE001
        info["pip_show_error"] = f"{type(exc).__name__}: {exc}"

    return info


def handler(job: dict[str, Any]) -> dict[str, Any]:
    global _FIRST_REQUEST, _MODEL_INIT_AT_LOAD

    try:
        job_input = job.get("input") or {}
        if job_input.get("_debug") == "env":
            return _debug_env()
        specs = _validate_and_normalize(job_input)

        worker_cold = _FIRST_REQUEST
        if not MODEL_LOADED:
            load_pipeline()
            _MODEL_INIT_AT_LOAD = MODEL_INIT_SECONDS
        model_init = _MODEL_INIT_AT_LOAD if worker_cold else 0.0

        results = []
        for i, spec in enumerate(specs):
            # Only the first job in a packed batch pays cold-start attribution.
            cold = worker_cold and i == 0
            results.append(
                _run_one(
                    spec,
                    worker_cold=cold,
                    model_init_seconds=model_init if cold else 0.0,
                )
            )

        _FIRST_REQUEST = False

        if len(results) == 1:
            return results[0]
        return {
            "count": len(results),
            "results": results,
            "timing": {
                "worker_cold": worker_cold,
                "model_init_seconds": round(model_init if worker_cold else 0.0, 3),
            },
        }
    except (ValueError, PipelineError, UpscaleError, UploadError) as exc:
        return {"error": str(exc), "error_type": type(exc).__name__}
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "traceback": traceback.format_exc()[-4000:],
        }


def _start_background_eager_load() -> None:
    """Optionally warm the model without blocking queue registration.

    Default is off. When enabled, load runs in a daemon thread so
    ``runpod.serverless.start`` can accept jobs immediately. Otherwise
    workers appear ready while stuck downloading H3 and jobs sit in queue.
    """
    if os.environ.get("H3_EAGER_LOAD", "0") != "1":
        return
    if os.environ.get("RUNPOD_LOCAL_TEST") == "1":
        return

    import threading

    def _bg() -> None:
        global _MODEL_INIT_AT_LOAD
        try:
            print("[handler] background eager model load starting", flush=True)
            load_pipeline()
            _MODEL_INIT_AT_LOAD = MODEL_INIT_SECONDS
            print(
                f"[handler] background eager model load done ({MODEL_INIT_SECONDS:.1f}s)",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"[handler] background eager load failed (will retry on first job): {exc}",
                flush=True,
            )

    threading.Thread(target=_bg, name="h3-eager-load", daemon=True).start()


if __name__ == "__main__":
    _start_background_eager_load()
    runpod.serverless.start({"handler": handler})
