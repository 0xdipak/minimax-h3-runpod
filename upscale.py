"""Upscale generated H3 video to TikTok 1080x1920 and preserve stereo audio."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class UpscaleError(RuntimeError):
    pass


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise UpscaleError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"stderr: {proc.stderr[-2000:]}"
        )


def upscale_to_tiktok(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Scale video to target resolution with high-quality filters; keep audio."""
    src = Path(input_path)
    if not src.is_file():
        raise UpscaleError(f"Input video not found: {src}")

    if shutil.which("ffmpeg") is None:
        raise UpscaleError("ffmpeg not found on PATH")

    dest = Path(output_path) if output_path else src.with_name(f"{src.stem}_{width}x{height}.mp4")
    dest.parent.mkdir(parents=True, exist_ok=True)

    mode = os.environ.get("UPSCALER", "ffmpeg").lower()
    if mode == "realesrgan":
        try:
            return _upscale_realesrgan(src, dest, width=width, height=height)
        except Exception as exc:  # noqa: BLE001 — fall back to ffmpeg
            print(f"[upscale] realesrgan failed ({exc}); falling back to ffmpeg")

    # Lanczos + light unsharp; force exact TikTok canvas.
    vf = (
        f"scale={width}:{height}:flags=lanczos:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        f"unsharp=5:5:0.6:5:5:0.0"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            os.environ.get("FFMPEG_PRESET", "medium"),
            "-crf",
            os.environ.get("FFMPEG_CRF", "16"),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )
    return dest


def _upscale_realesrgan(src: Path, dest: Path, *, width: int, height: int) -> Path:
    """Optional Real-ESRGAN path when realesrgan CLI / package is installed."""
    if shutil.which("realesrgan-ncnn-vulkan"):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "up.mp4"
            # Frame-free path: many builds only do images; use ffmpeg after 2x/4x if available.
            _run(
                [
                    "realesrgan-ncnn-vulkan",
                    "-i",
                    str(src),
                    "-o",
                    str(tmp),
                    "-n",
                    "realesrgan-x4plus",
                ]
            )
            return upscale_to_tiktok(tmp, dest, width=width, height=height)

    # Python package path (optional dependency)
    from basicsr.archs.rrdbnet_arch import RRDBNet  # type: ignore
    from realesrgan import RealESRGANer  # type: ignore
    import cv2
    import numpy as np

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    upsampler = RealESRGANer(
        scale=4,
        model_path=os.environ.get(
            "REALESRGAN_MODEL_PATH",
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        ),
        model=model,
        tile=0,
        half=True,
    )

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise UpscaleError("OpenCV failed to open video")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames: list[np.ndarray] = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        out, _ = upsampler.enhance(frame, outscale=4)
        frames.append(cv2.resize(out, (width, height), interpolation=cv2.INTER_LANCZOS4))
    cap.release()
    if not frames:
        raise UpscaleError("No frames decoded for realesrgan")

    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "video_only.mp4"
        h, w = frames[0].shape[:2]
        writer = cv2.VideoWriter(
            str(raw),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (w, h),
        )
        for f in frames:
            writer.write(f)
        writer.release()
        # remux original audio
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(raw),
                "-i",
                str(src),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0?",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "16",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(dest),
            ]
        )
    return dest
