"""CLI entrypoint and argument parser for video-upscale."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from video_upscaler import (
    DenoiseLevel,
    FitStrategy,
    Preset,
    QualityProfile,
    UpscaleConfig,
    Upscaler,
    VideoProbe,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-upscale",
        description="High-precision video upscaler using FFmpeg filter pipelines.",
    )

    parser.add_argument("input", help="Input video file path.")
    parser.add_argument(
        "-o", "--output",
        help="Output video file path. Defaults to <input>_<preset>.mp4 next to the input.",
    )

    parser.add_argument(
        "-p", "--preset",
        choices=[p.value for p in Preset],
        default=Preset.RES_1080P.value,
        help="Target resolution preset (default: 1080p).",
    )

    parser.add_argument(
        "--fit",
        choices=[f.value for f in FitStrategy],
        default=FitStrategy.FIT.value,
        help="Canvas fit strategy: fit (default), pad, or crop.",
    )

    parser.add_argument(
        "--quality",
        choices=[q.value for q in QualityProfile],
        default=QualityProfile.MEDIUM.value,
        help="Encoding quality/speed trade-off (default: medium).",
    )

    parser.add_argument(
        "--denoise",
        choices=[d.value for d in DenoiseLevel],
        default=DenoiseLevel.GENTLE.value,
        help="Denoise filtering intensity (default: gentle).",
    )

    parser.add_argument(
        "--no-sharpen",
        action="store_true",
        help="Disable the unsharp sharpening filter.",
    )

    parser.add_argument(
        "--deband",
        action="store_true",
        help="Enable debanding filter to reduce gradient banding.",
    )

    parser.add_argument(
        "--codec",
        default="libx264",
        help="Video codec (default: libx264).",
    )

    parser.add_argument(
        "--scale",
        type=float,
        metavar="N",
        help="Scale factor (e.g. 2 for 2x). Overrides --preset when set.",
    )

    parser.add_argument(
        "--width",
        type=int,
        metavar="W",
        help="Custom canvas width (requires --preset custom or --height).",
    )

    parser.add_argument(
        "--height",
        type=int,
        metavar="H",
        help="Custom canvas height (requires --preset custom or --width).",
    )

    parser.add_argument(
        "--dci",
        action="store_true",
        help="Use DCI 2K (2048x1080) instead of QHD 2K (2560x1440) with --preset 2k.",
    )

    parser.add_argument(
        "--allow-low-res",
        action="store_true",
        help="Allow upscaling inputs below 360p.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for video-upscale CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    # Default output path: <stem>_<preset>.mp4 next to the input
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        preset_tag = args.preset
        if args.scale is not None:
            preset_tag = f"{args.scale}x"
        output_path = input_path.with_name(f"{input_path.stem}_{preset_tag}.mp4")

    # Build config
    preset = Preset.from_str(args.preset)
    if args.scale is not None:
        preset = Preset.CUSTOM

    config = UpscaleConfig(
        preset=preset,
        fit=FitStrategy.from_str(args.fit),
        quality=QualityProfile(args.quality),
        denoise=DenoiseLevel(args.denoise),
        sharpen=not args.no_sharpen,
        deband=args.deband,
        codec=args.codec,
        allow_low_res=args.allow_low_res,
        scale_factor=args.scale,
        custom_w=args.width,
        custom_h=args.height,
        dci=args.dci,
    )

    upscaler = Upscaler(config)

    try:
        result = upscaler.upscale(
            input_path,
            output_path,
        )
    except Exception as exc:  # noqa: BLE001 — surface any upscale failure cleanly
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Upscaled: {result.output_path}")
    print(f"Resolution: {result.width}x{result.height}")
    print(f"Duration: {result.duration:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
