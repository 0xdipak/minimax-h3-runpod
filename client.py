#!/usr/bin/env python3
"""Submit a single H3 job to a Runpod Serverless Queue endpoint (or local handler)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
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


def run_local(job_input: dict[str, Any]) -> dict[str, Any]:
    os.environ["RUNPOD_LOCAL_TEST"] = "1"
    os.environ["H3_EAGER_LOAD"] = "0"
    from handler import handler

    return handler({"id": "local", "input": job_input})


def run_remote(
    endpoint_id: str,
    api_key: str,
    job_input: dict[str, Any],
    *,
    sync: bool,
    poll_seconds: float,
    timeout: float,
) -> dict[str, Any]:
    base = f"https://api.runpod.ai/v2/{endpoint_id}"
    if sync:
        return post_json(f"{base}/runsync", {"input": job_input}, api_key)

    submitted = post_json(f"{base}/run", {"input": job_input}, api_key)
    job_id = submitted.get("id")
    if not job_id:
        return submitted

    print(f"Submitted job {job_id}", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = get_json(f"{base}/status/{job_id}", api_key)
        state = status.get("status")
        print(f"  status={state}", flush=True)
        if state in {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}:
            return status
        time.sleep(poll_seconds)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")


def print_result(result: dict[str, Any]) -> int:
    # Runpod wraps output
    output = result.get("output", result)
    if isinstance(output, dict) and output.get("error"):
        print(f"ERROR ({output.get('error_type')}): {output['error']}", file=sys.stderr)
        if output.get("traceback"):
            print(output["traceback"], file=sys.stderr)
        return 1

    if isinstance(output, dict) and output.get("cli_summary"):
        print(output["cli_summary"])
        print()
        print(json.dumps(output, indent=2))
        return 0

    print(json.dumps(result, indent=2))
    return 0 if not (isinstance(output, dict) and output.get("error")) else 1


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description="MiniMax H3 Runpod client")
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--input", type=Path, default=Path("test_input.json"))
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--aspect-ratio", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--quality", default=None, help="draft|720p|native")
    parser.add_argument("--no-upscale", action="store_true")
    parser.add_argument("--local", action="store_true", help="Call handler locally")
    parser.add_argument("--sync", action="store_true", help="Use /runsync")
    parser.add_argument("--endpoint-id", default=os.environ.get("RUNPOD_ENDPOINT_ID"))
    parser.add_argument("--api-key", default=os.environ.get("RUNPOD_API_KEY"))
    parser.add_argument("--poll", type=float, default=15.0)
    parser.add_argument("--timeout", type=float, default=7200.0)
    args = parser.parse_args()

    if args.input.is_file():
        payload = json.loads(args.input.read_text())
        job_input = payload.get("input", payload)
    else:
        job_input = {}

    if args.prompt:
        job_input["prompt"] = args.prompt
    if args.duration is not None:
        job_input["duration"] = args.duration
    if args.aspect_ratio:
        job_input["aspect_ratio"] = args.aspect_ratio
    if args.seed is not None:
        job_input["seed"] = args.seed
    if args.quality:
        job_input["resolution_preset"] = args.quality
    if args.no_upscale:
        job_input["upscale"] = False

    if "prompt" not in job_input:
        print("prompt is required (via --prompt or test_input.json)", file=sys.stderr)
        return 2

    try:
        if args.local:
            result = run_local(job_input)
        else:
            if not args.endpoint_id or not args.api_key:
                print(
                    "RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY required (or use --local)",
                    file=sys.stderr,
                )
                return 2
            result = run_remote(
                args.endpoint_id,
                args.api_key,
                job_input,
                sync=args.sync,
                poll_seconds=args.poll,
                timeout=args.timeout,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"HTTP {exc.code}: {body}", file=sys.stderr)
        return 1

    return print_result(result)


if __name__ == "__main__":
    raise SystemExit(main())
