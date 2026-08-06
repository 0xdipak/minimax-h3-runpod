#!/usr/bin/env python3
"""Submit N independent Runpod Queue jobs to amortize H3 cold-start cost."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def post_json(url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def get_json(url: str, api_key: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def submit_and_wait(
    endpoint_id: str,
    api_key: str,
    job_input: dict[str, Any],
    *,
    poll: float,
    timeout: float,
) -> dict[str, Any]:
    base = f"https://api.runpod.ai/v2/{endpoint_id}"
    submitted = post_json(f"{base}/run", {"input": job_input}, api_key)
    job_id = submitted["id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = get_json(f"{base}/status/{job_id}", api_key)
        if status.get("status") in {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}:
            status["_job_id"] = job_id
            return status
        time.sleep(poll)
    raise TimeoutError(job_id)


def extract_cost_fields(status: dict[str, Any]) -> dict[str, Any]:
    out = status.get("output") or {}
    cost = out.get("cost") or {}
    timing = out.get("timing") or {}
    return {
        "job_id": status.get("_job_id") or status.get("id"),
        "status": status.get("status"),
        "worker_cold": timing.get("worker_cold"),
        "billed_seconds": (cost.get("billed_seconds") or timing.get("billed_seconds_estimate")),
        "runpod_cost": cost.get("estimated_runpod_cost"),
        "cost_per_output_second": cost.get("cost_per_output_second"),
        "output_seconds": out.get("duration"),
        "delay_time_ms": status.get("delayTime"),
        "execution_time_ms": status.get("executionTime"),
        "error": out.get("error"),
    }


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description="Burst-submit H3 jobs")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--prompt", required=False)
    parser.add_argument("--input", type=Path, default=Path("test_input.json"))
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--quality", default="draft")
    parser.add_argument("--no-upscale", action="store_true")
    parser.add_argument("--endpoint-id", default=os.environ.get("RUNPOD_ENDPOINT_ID"))
    parser.add_argument("--api-key", default=os.environ.get("RUNPOD_API_KEY"))
    parser.add_argument("--poll", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=10800.0)
    parser.add_argument("--submit-workers", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("docs/burst_results.json"))
    args = parser.parse_args()

    if not args.endpoint_id or not args.api_key:
        print("RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY required")
        return 2

    if args.input.is_file():
        base_input = json.loads(args.input.read_text()).get("input", {})
    else:
        base_input = {}
    prompt = args.prompt or base_input.get("prompt")
    if not prompt:
        print("prompt required")
        return 2

    job_input = {
        "prompt": prompt,
        "duration": args.duration,
        "aspect_ratio": "9:16",
        "resolution_preset": args.quality,
        "upscale": not args.no_upscale,
    }

    print(f"Submitting {args.count} independent jobs...", flush=True)
    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=args.submit_workers) as pool:
        futs = [
            pool.submit(
                submit_and_wait,
                args.endpoint_id,
                args.api_key,
                {**job_input, "seed": 1000 + i},
                poll=args.poll,
                timeout=args.timeout,
            )
            for i in range(args.count)
        ]
        for fut in as_completed(futs):
            status = fut.result()
            fields = extract_cost_fields(status)
            results.append(fields)
            print(
                f"  {fields['job_id']}: {fields['status']} "
                f"cold={fields['worker_cold']} cost={fields['runpod_cost']}",
                flush=True,
            )

    elapsed = time.perf_counter() - t0
    completed = [r for r in results if r["status"] == "COMPLETED" and r.get("runpod_cost") is not None]
    cold = [r for r in completed if r.get("worker_cold")]
    warm = [r for r in completed if r.get("worker_cold") is False]

    def avg(vals: list[float]) -> float:
        return statistics.mean(vals) if vals else 0.0

    report = {
        "count": args.count,
        "elapsed_wall_seconds": round(elapsed, 2),
        "completed": len(completed),
        "failed": len(results) - len(completed),
        "cold_avg_cost": round(avg([r["runpod_cost"] for r in cold]), 6),
        "warm_avg_cost": round(avg([r["runpod_cost"] for r in warm]), 6),
        "all_avg_cost": round(avg([r["runpod_cost"] for r in completed]), 6),
        "warm_avg_cost_per_output_sec": round(
            avg([r["cost_per_output_second"] for r in warm if r.get("cost_per_output_second")]),
            6,
        ),
        "batch_avg_cost_per_output_sec": round(
            avg([r["cost_per_output_second"] for r in completed if r.get("cost_per_output_second")]),
            6,
        ),
        "results": results,
    }

    # Pretty economics block
    minimax = float(os.environ.get("MINIMAX_RATE_PER_SEC", "0.13"))
    batch_cps = report["batch_avg_cost_per_output_sec"]
    savings = ((minimax - batch_cps) / minimax * 100.0) if minimax and batch_cps else 0.0
    print()
    print(f"Cold generation:        ${report['cold_avg_cost']:.4f}")
    print(f"Warm generation:        ${report['warm_avg_cost']:.4f}")
    print(f"{args.count}-job burst avg:     ${report['all_avg_cost']:.4f}")
    if cold and warm:
        overhead = report["cold_avg_cost"] - report["warm_avg_cost"]
        print(f"Cold-start overhead:     ${overhead:.4f}")
    print(f"Warm $/output-sec:       ${report['warm_avg_cost_per_output_sec']:.4f}")
    print(f"Batch $/output-sec:      ${batch_cps:.4f}")
    print(f"MiniMax baseline:        ${minimax:.4f}")
    print(f"Savings vs MiniMax:      {savings:.1f}%")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {args.out}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
