"""Configurable Runpod vs MiniMax cost instrumentation."""

from __future__ import annotations

import os
from typing import Any


DEFAULT_GPU_RATES: dict[str, float] = {
    # Runpod Serverless $/second (docs, Aug 2026)
    "A4000": 0.00016,
    "A4500": 0.00016,
    "RTX_4000": 0.00016,
    "L4": 0.00019,
    "A5000": 0.00019,
    "3090": 0.00019,
    "4090": 0.00031,
    "A6000": 0.00034,
    "A40": 0.00034,
    "L40": 0.00053,
    "L40S": 0.00053,
    "6000_ADA": 0.00053,
    "A100": 0.00076,
    "H100": 0.00116,
    "6000_PRO": 0.00111,
    "H200": 0.00155,
    "B200": 0.00240,
}


def gpu_rate_per_second(gpu_type: str | None = None) -> float:
    override = os.environ.get("RUNPOD_GPU_RATE_PER_SEC")
    if override:
        return float(override)
    name = (gpu_type or os.environ.get("RUNPOD_GPU_TYPE") or "L40S").upper()
    # normalize common variants
    key = (
        name.replace(" ", "_")
        .replace("-", "_")
        .replace("RTX_", "")
        .replace("NVIDIA_", "")
    )
    for candidate in (name, key, key.replace("RTX_", "")):
        if candidate in DEFAULT_GPU_RATES:
            return DEFAULT_GPU_RATES[candidate]
    # fuzzy
    for k, v in DEFAULT_GPU_RATES.items():
        if k in key or key in k:
            return v
    return DEFAULT_GPU_RATES["L40S"]


def minimax_rate_per_second() -> float:
    return float(os.environ.get("MINIMAX_RATE_PER_SEC", "0.13"))


def compute_cost(
    *,
    billed_seconds: float,
    output_seconds: float,
    gpu_type: str | None = None,
) -> dict[str, Any]:
    rate = gpu_rate_per_second(gpu_type)
    minimax_rate = minimax_rate_per_second()
    runpod_cost = billed_seconds * rate
    cost_per_out = (runpod_cost / output_seconds) if output_seconds > 0 else 0.0
    minimax_eq = output_seconds * minimax_rate
    savings = ((minimax_eq - runpod_cost) / minimax_eq * 100.0) if minimax_eq > 0 else 0.0
    return {
        "gpu_type": gpu_type or os.environ.get("RUNPOD_GPU_TYPE") or "unknown",
        "rate_per_second": round(rate, 6),
        "estimated_runpod_cost": round(runpod_cost, 6),
        "cost_per_output_second": round(cost_per_out, 6),
        "minimax_equivalent": round(minimax_eq, 6),
        "minimax_rate_per_second": minimax_rate,
        "savings_pct": round(savings, 2),
        "billed_seconds": round(billed_seconds, 3),
    }


def format_cli_summary(
    *,
    output_seconds: float,
    native_w: int,
    native_h: int,
    out_w: int,
    out_h: int,
    gpu_compute_seconds: float,
    cost: dict[str, Any],
) -> str:
    res = f"{native_w}x{native_h}"
    if (out_w, out_h) != (native_w, native_h):
        res = f"{native_w}x{native_h} -> {out_w}x{out_h}"
    return (
        "H3 generation complete\n"
        f"Output: {output_seconds:.1f} sec\n"
        f"Resolution: {res}\n"
        f"GPU compute: {gpu_compute_seconds:.1f} sec\n"
        f"Estimated Runpod cost: ${cost['estimated_runpod_cost']:.3f}\n"
        f"Cost/output-sec: ${cost['cost_per_output_second']:.4f}\n"
        f"MiniMax equivalent: ${cost['minimax_equivalent']:.2f}\n"
        f"Savings: {cost['savings_pct']:.1f}%"
    )
