"""MiniMax H3 load-once pipeline (diffusers ModularPipeline, t2va / FL2VA)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Timing populated at worker init
MODEL_INIT_SECONDS: float = 0.0
MODEL_LOADED: bool = False
_PIPE = None
_MANAGER = None


RESOLUTION_PRESETS: dict[str, dict[str, int]] = {
    # All multiples of 32; 9:16 vertical
    "draft": {"width": 544, "height": 960},
    "720p": {"width": 720, "height": 1280},
    "native": {"width": 768, "height": 1344},
}

ASPECT_SIZES: dict[str, dict[str, dict[str, int]]] = {
    "9:16": RESOLUTION_PRESETS,
    "16:9": {
        "draft": {"width": 960, "height": 544},
        "720p": {"width": 1280, "height": 720},
        "native": {"width": 1344, "height": 768},
    },
    "1:1": {
        "draft": {"width": 704, "height": 704},
        "720p": {"width": 768, "height": 768},
        "native": {"width": 768, "height": 768},
    },
}

FPS = 24
MIN_DURATION = 5.0
MAX_DURATION = 15.0


class PipelineError(RuntimeError):
    pass


@dataclass
class GenerateResult:
    video_path: Path
    width: int
    height: int
    duration: float
    num_frames: int
    seed: int
    inference_seconds: float
    num_inference_steps: int


def resolve_model_path() -> str:
    """Prefer Runpod cached HF model path when present."""
    override = os.environ.get("H3_MODEL_PATH")
    if override and Path(override).exists():
        return override

    cached_root = Path("/runpod-volume/huggingface-cache/hub/models--MiniMaxAI--MiniMax-H3")
    if cached_root.is_dir():
        snaps = cached_root / "snapshots"
        if snaps.is_dir():
            candidates = sorted(snaps.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            for c in candidates:
                if (c / "modular_model_index.json").exists() or (c / "model_index.json").exists():
                    return str(c)
        # refs/main may point at snapshot
        ref = cached_root / "refs" / "main"
        if ref.is_file():
            snap = cached_root / "snapshots" / ref.read_text().strip()
            if snap.is_dir():
                return str(snap)

    return os.environ.get("H3_MODEL_ID", "MiniMaxAI/MiniMax-H3")


def duration_to_num_frames(duration_sec: float) -> tuple[int, float]:
    """Snap duration to H3's 17n+5 frame grid at 24fps."""
    duration_sec = max(MIN_DURATION, min(MAX_DURATION, float(duration_sec)))
    target = int(round(duration_sec * FPS))
    # find smallest 17n+5 >= target (or closest)
    n = max(0, (target - 5 + 16) // 17)
    frames = 17 * n + 5
    # keep within duration window
    while frames / FPS > MAX_DURATION and n > 0:
        n -= 1
        frames = 17 * n + 5
    while frames / FPS < MIN_DURATION:
        n += 1
        frames = 17 * n + 5
    return frames, frames / FPS


def resolve_resolution(aspect_ratio: str, preset: str) -> tuple[int, int]:
    aspect = aspect_ratio.strip()
    table = ASPECT_SIZES.get(aspect)
    if table is None:
        raise PipelineError(
            f"Unsupported aspect_ratio '{aspect_ratio}'. "
            f"Supported: {', '.join(sorted(ASPECT_SIZES))}"
        )
    key = preset.strip().lower()
    if key not in table:
        raise PipelineError(
            f"Unsupported resolution_preset '{preset}'. Supported: {', '.join(sorted(table))}"
        )
    w, h = table[key]["width"], table[key]["height"]
    if w % 32 or h % 32:
        raise PipelineError(f"Resolution {w}x{h} must be multiples of 32")
    return w, h


def detect_memory_mode() -> str:
    mode = os.environ.get("H3_MEMORY_MODE", "auto").lower()
    if mode != "auto":
        return mode
    try:
        import torch

        if not torch.cuda.is_available():
            return "int8_group_offload"
        props = torch.cuda.get_device_properties(0)
        vram_gb = props.total_memory / (1024**3)
        if vram_gb >= 70:
            return "a100_bf16_offload"
        return "int8_group_offload"
    except Exception:  # noqa: BLE001
        return "int8_group_offload"


def _try_set_attention_backend(pipe: Any) -> str:
    backend = os.environ.get("H3_ATTENTION_BACKEND", "auto")
    transformer = getattr(pipe, "transformer", None)
    if transformer is None or not hasattr(transformer, "set_attention_backend"):
        return "default"
    if backend == "sdpa":
        return "sdpa"
    candidates: list[str]
    if backend != "auto":
        candidates = [backend]
    else:
        # Hopper flash-3 first, then sage, then sdpa
        candidates = ["_flash_3_hub", "sage_attention", "flash_attention_2", "sdpa"]
    for name in candidates:
        try:
            transformer.set_attention_backend(name)
            return name
        except Exception as exc:  # noqa: BLE001
            print(f"[h3] attention backend {name} unavailable: {exc}")
    return "default"


def load_pipeline() -> Any:
    """Load H3 once for the worker lifecycle."""
    global _PIPE, _MANAGER, MODEL_INIT_SECONDS, MODEL_LOADED
    if MODEL_LOADED and _PIPE is not None:
        return _PIPE

    t0 = time.perf_counter()
    import torch

    from diffusers import ModularPipeline

    model_path = resolve_model_path()
    memory_mode = detect_memory_mode()
    print(f"[h3] loading model from {model_path} mode={memory_mode}", flush=True)
    print("[h3] stage=resolve_components (CPU/network; VRAM stays low until denoise)", flush=True)

    if memory_mode == "a100_bf16_offload":
        from diffusers import ComponentsManager

        # Official recipe: keep all workflows on the pipeline; select components
        # via load_components(workflow=...). Passing workflow= to from_pretrained
        # prunes to SequentialPipelineBlocks without a workflow map.
        manager = ComponentsManager()
        pipe = ModularPipeline.from_pretrained(
            model_path,
            components_manager=manager,
        )
        print("[h3] stage=load_components t2va (download+deserialize; expect empty VRAM)", flush=True)
        pipe.load_components(workflow="t2va", dtype=torch.bfloat16)
        print("[h3] stage=enable_auto_cpu_offload", flush=True)
        manager.enable_auto_cpu_offload(
            device="cuda",
            memory_reserve_margin=os.environ.get("H3_MEMORY_RESERVE", "48GB"),
        )
        _MANAGER = manager
        _PIPE = pipe
    elif memory_mode == "int8_group_offload":
        from diffusers import MiniMaxH3Transformer3DModel, TorchAoConfig
        from diffusers.hooks import apply_group_offloading
        from torchao.quantization import Int8WeightOnlyConfig
        from transformers import Qwen3VLForConditionalGeneration
        from transformers import TorchAoConfig as TransformersTorchAoConfig

        pipe = ModularPipeline.from_pretrained(model_path)
        pipe.update_components(
            transformer=MiniMaxH3Transformer3DModel.from_pretrained(
                model_path,
                subfolder="transformer",
                dtype=torch.bfloat16,
                quantization_config=TorchAoConfig(
                    Int8WeightOnlyConfig(version=2),
                    modules_to_not_convert=[
                        "proj_in",
                        "audio_proj_in",
                        "context_embedder",
                        "time_embedder",
                        "time_proj",
                        "token_refiner",
                        "norm_out",
                        "proj_out",
                        "audio_proj_out",
                    ],
                ),
                low_cpu_mem_usage=False,
            ),
            text_encoder=Qwen3VLForConditionalGeneration.from_pretrained(
                model_path,
                subfolder="text_encoder",
                dtype=torch.bfloat16,
                quantization_config=TransformersTorchAoConfig(
                    Int8WeightOnlyConfig(version=2),
                    modules_to_not_convert=[
                        "model.visual",
                        "model.language_model.embed_tokens",
                        "model.language_model.norm",
                        "lm_head",
                    ],
                ),
            ),
        )
        pipe.load_components(workflow="t2va", dtype=torch.bfloat16)
        pipe.transformer.requires_grad_(False)
        pipe.text_encoder.requires_grad_(False)
        offload = dict(
            onload_device=torch.device("cuda"),
            offload_device=torch.device("cpu"),
            use_stream=True,
        )
        pipe.transformer.enable_group_offload(
            offload_type="block_level",
            num_blocks_per_group=int(os.environ.get("H3_OFFLOAD_BLOCKS", "1")),
            **offload,
        )
        apply_group_offloading(pipe.text_encoder.model, offload_type="leaf_level", **offload)
        pipe.vae.to("cuda")
        pipe.audio_vae.to("cuda")
        _PIPE = pipe
    else:
        raise PipelineError(
            f"Unknown H3_MEMORY_MODE={memory_mode}. "
            "Use auto | a100_bf16_offload | int8_group_offload"
        )

    attn = _try_set_attention_backend(_PIPE)
    print(f"[h3] attention backend: {attn}")

    MODEL_INIT_SECONDS = time.perf_counter() - t0
    MODEL_LOADED = True
    print(f"[h3] model ready in {MODEL_INIT_SECONDS:.1f}s")
    return _PIPE


def generate(
    *,
    prompt: str,
    duration: float = 10.0,
    aspect_ratio: str = "9:16",
    resolution_preset: str = "native",
    seed: int | None = None,
    num_inference_steps: int | None = None,
    output_dir: str | Path | None = None,
) -> GenerateResult:
    import torch
    from diffusers.utils.export_utils import encode_video

    if not prompt or not str(prompt).strip():
        raise PipelineError("prompt is required")

    pipe = load_pipeline()
    width, height = resolve_resolution(aspect_ratio, resolution_preset)
    num_frames, snapped_duration = duration_to_num_frames(duration)
    steps = int(num_inference_steps or os.environ.get("H3_NUM_INFERENCE_STEPS", "20"))
    if seed is None:
        seed = int.from_bytes(os.urandom(4), "little")
    seed = int(seed)

    out_root = Path(output_dir or os.environ.get("OUTPUT_DIR", "/tmp/h3_outputs"))
    out_root.mkdir(parents=True, exist_ok=True)
    out_path = out_root / f"h3_{seed}_{width}x{height}_{num_frames}f.mp4"

    generator = torch.Generator(device="cpu").manual_seed(seed)
    outputs = ["videos", "audio", "sampling_rate"]

    t0 = time.perf_counter()
    results = pipe(
        prompt=prompt,
        num_frames=num_frames,
        height=height,
        width=width,
        num_inference_steps=steps,
        generator=generator,
        output=outputs,
    )
    inference_seconds = time.perf_counter() - t0

    encode_video(
        results["videos"][0],
        fps=FPS,
        output_path=str(out_path),
        audio=results["audio"][0],
        audio_sample_rate=results["sampling_rate"],
    )

    if not out_path.is_file() or out_path.stat().st_size < 1000:
        raise PipelineError("Generation produced an empty or missing video file")

    return GenerateResult(
        video_path=out_path,
        width=width,
        height=height,
        duration=snapped_duration,
        num_frames=num_frames,
        seed=seed,
        inference_seconds=inference_seconds,
        num_inference_steps=steps,
    )


def detect_gpu_name() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get("RUNPOD_GPU_TYPE", "unknown")
