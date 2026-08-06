#!/usr/bin/env python3
"""Resolution + cold/warm economics benchmarks for H3 on Runpod."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from burst import extract_cost_fields, submit_and_wait
from client import _load_dotenv, run_remote


REPRESENTATIVE_PROMPT = (
    "Vertical TikTok product ad, 9:16. A young creator holds a matte black water bottle "
    "on a sunny rooftop. Shot 1 (0-3s): quick push-in, city bokeh behind, upbeat lo-fi beat. "
    "Shot 2 (3-7s): bottle twists open, crisp pour SFX, soft smile to camera. "
    "Shot 3 (7-10s): hold product label centered, energetic whoosh transition, "
    "on-screen text vibe only in the scene lighting, no logos invented."
)


def run_one(
    endpoint_id: str,
    api_key: str,
    *,
    quality: str,
    duration: float,
    seed: int,
    upscale: bool,
    poll: float,
    timeout: float,
) -> dict[str, Any]:
    job_input = {
        "prompt": REPRESENTATIVE_PROMPT,
        "duration": duration,
        "aspect_ratio": "9:16",
        "resolution_preset": quality,
        "seed": seed,
        "upscale": upscale,
    }
    status = run_remote(
        endpoint_id,
        api_key,
        job_input,
        sync=False,
        poll_seconds=poll,
        timeout=timeout,
    )
    fields = extract_cost_fields(status)
    out = status.get("output") or {}
    fields.update(
        {
            "native_width": out.get("native_width"),
            "native_height": out.get("native_height"),
            "width": out.get("width"),
            "height": out.get("height"),
            "inference_seconds": (out.get("timing") or {}).get("inference_seconds"),
            "video_url": out.get("video_url"),
            "quality_notes": "",
        }
    )
    return fields


def markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = [
        "native resolution",
        "inference config",
        "generation time (s)",
        "output seconds",
        "estimated cost",
        "$/output-second",
        "relative quality notes",
        "savings vs $0.13/sec",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for r in rows:
        native = f"{r.get('native_width')}x{r.get('native_height')}"
        cfg = r.get("config", "")
        gen = r.get("inference_seconds")
        out_s = r.get("output_seconds")
        cost = r.get("runpod_cost")
        cps = r.get("cost_per_output_second")
        notes = r.get("quality_notes") or ""
        minimax = 0.13
        savings = ""
        if cps is not None:
            savings = f"{((minimax - cps) / minimax * 100):.1f}%"
        lines.append(
            "| "
            + " | ".join(
                [
                    native,
                    cfg,
                    f"{gen:.1f}" if isinstance(gen, (int, float)) else "",
                    f"{out_s:.2f}" if isinstance(out_s, (int, float)) else "",
                    f"${cost:.4f}" if isinstance(cost, (int, float)) else "",
                    f"${cps:.4f}" if isinstance(cps, (int, float)) else "",
                    notes,
                    savings,
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-id", default=os.environ.get("RUNPOD_ENDPOINT_ID"))
    parser.add_argument("--api-key", default=os.environ.get("RUNPOD_API_KEY"))
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--poll", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=10800.0)
    parser.add_argument("--skip-burst", action="store_true")
    parser.add_argument("--burst-count", type=int, default=10)
    parser.add_argument("--out", type=Path, default=Path("docs/benchmark_results.md"))
    args = parser.parse_args()

    if not args.endpoint_id or not args.api_key:
        print("RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY required")
        return 2

    rows: list[dict[str, Any]] = []
    matrix = [
        ("draft", True, "draft 544x960 + upscale"),
        ("720p", True, "720x1280 + upscale"),
        ("native", True, "native 768x1344 + upscale"),
    ]

    print("=== Resolution matrix ===", flush=True)
    for i, (quality, upscale, label) in enumerate(matrix):
        print(f"Running {label}...", flush=True)
        # Small delay so workers can scale down between matrix points if desired;
        # first is cold-ish, later may be warm depending on idle timeout.
        if i > 0:
            time.sleep(5)
        row = run_one(
            args.endpoint_id,
            args.api_key,
            quality=quality,
            duration=args.duration,
            seed=42 + i,
            upscale=upscale,
            poll=args.poll,
            timeout=args.timeout,
        )
        row["config"] = label
        row["quality_notes"] = "auto; inspect video_url"
        rows.append(row)
        print(json.dumps(row, indent=2), flush=True)

    economics: dict[str, Any] = {}
    print("=== Cold / warm pair ===", flush=True)
    # Encourage scale-to-zero between matrix and cold test
    idle_wait = int(os.environ.get("BENCH_IDLE_WAIT_SECONDS", "150"))
    print(f"Waiting {idle_wait}s for possible scale-to-zero...", flush=True)
    time.sleep(idle_wait)

    cold = run_one(
        args.endpoint_id,
        args.api_key,
        quality="draft",
        duration=args.duration,
        seed=9001,
        upscale=True,
        poll=args.poll,
        timeout=args.timeout,
    )
    warm = run_one(
        args.endpoint_id,
        args.api_key,
        quality="draft",
        duration=args.duration,
        seed=9002,
        upscale=True,
        poll=args.poll,
        timeout=args.timeout,
    )
    economics["cold"] = cold
    economics["warm"] = warm

    burst_summary = None
    if not args.skip_burst:
        print(f"=== {args.burst_count}-job burst ===", flush=True)
        # Reuse burst.submit path inline for independence
        from concurrent.futures import ThreadPoolExecutor, as_completed

        job_input = {
            "prompt": REPRESENTATIVE_PROMPT,
            "duration": args.duration,
            "aspect_ratio": "9:16",
            "resolution_preset": "draft",
            "upscale": True,
        }
        burst_rows: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(8, args.burst_count)) as pool:
            futs = [
                pool.submit(
                    submit_and_wait,
                    args.endpoint_id,
                    args.api_key,
                    {**job_input, "seed": 7000 + i},
                    poll=args.poll,
                    timeout=args.timeout,
                )
                for i in range(args.burst_count)
            ]
            for fut in as_completed(futs):
                burst_rows.append(extract_cost_fields(fut.result()))

        completed = [r for r in burst_rows if r.get("runpod_cost") is not None]
        warm_b = [r for r in completed if r.get("worker_cold") is False]
        cold_b = [r for r in completed if r.get("worker_cold")]

        def avg(xs: list[float]) -> float:
            return sum(xs) / len(xs) if xs else 0.0

        burst_summary = {
            "count": args.burst_count,
            "cold_avg_cost": avg([r["runpod_cost"] for r in cold_b]),
            "warm_avg_cost": avg([r["runpod_cost"] for r in warm_b]),
            "all_avg_cost": avg([r["runpod_cost"] for r in completed]),
            "warm_cps": avg(
                [r["cost_per_output_second"] for r in warm_b if r.get("cost_per_output_second")]
            ),
            "batch_cps": avg(
                [r["cost_per_output_second"] for r in completed if r.get("cost_per_output_second")]
            ),
            "results": burst_rows,
        }
        economics["burst"] = burst_summary

    minimax = float(os.environ.get("MINIMAX_RATE_PER_SEC", "0.13"))
    cold_cost = cold.get("runpod_cost") or 0
    warm_cost = warm.get("runpod_cost") or 0
    overhead_cost = max(0.0, cold_cost - warm_cost)
    overhead_sec = None
    if cold.get("billed_seconds") and warm.get("billed_seconds"):
        overhead_sec = max(0.0, cold["billed_seconds"] - warm["billed_seconds"])

    batch_cps = (burst_summary or {}).get("batch_cps") or warm.get("cost_per_output_second") or 0
    savings = ((minimax - batch_cps) / minimax * 100.0) if minimax else 0.0

    md = []
    md.append("# MiniMax H3 Runpod Cost Benchmarks")
    md.append("")
    md.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    md.append("")
    md.append("Decision metric: **cost per usable finished TikTok** (1080×1920 when upscaled).")
    md.append("")
    md.append("## Resolution matrix (same 10s prompt)")
    md.append("")
    md.append(markdown_table(rows))
    md.append("")
    md.append("## Cold-start amortization")
    md.append("")
    md.append("```text")
    md.append(f"Cold generation:        ${cold_cost:.4f}")
    md.append(f"Warm generation:        ${warm_cost:.4f}")
    if burst_summary:
        md.append(f"10-job burst avg:        ${burst_summary['all_avg_cost']:.4f}")
    if overhead_sec is not None:
        md.append(f"Cold-start overhead:     {overhead_sec:.1f} sec / ${overhead_cost:.4f}")
    else:
        md.append(f"Cold-start overhead:     ${overhead_cost:.4f}")
    md.append(f"Warm $/output-sec:       ${(warm.get('cost_per_output_second') or 0):.4f}")
    md.append(f"Batch $/output-sec:      ${batch_cps:.4f}")
    md.append(f"MiniMax baseline:        ${minimax:.4f}")
    md.append(f"Savings vs MiniMax:      {savings:.1f}%")
    md.append("```")
    md.append("")
    md.append("## Raw JSON")
    md.append("")
    md.append("```json")
    md.append(
        json.dumps(
            {"matrix": rows, "economics": economics},
            indent=2,
            default=str,
        )
    )
    md.append("```")
    md.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(md))
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
