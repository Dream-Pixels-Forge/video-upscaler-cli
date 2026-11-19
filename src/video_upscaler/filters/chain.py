"""Precision filter chain builder (SPEC.md §3).

Assembles the ffmpeg video filter chain: denoise -> scale (lanczos) ->
sharpen -> deband, comma-joined for use with `-vf`.
"""

from typing import List

_DENOISE_FILTERS = {
    "none": None,
    "gentle": "hqdn3d=1.5:1.5:3:3",
    "medium": "hqdn3d=3:3:6:6",
    "strong": "atadenoise",
}

_SHARPEN_FILTER = "unsharp=lx=5:ly=5:la=0.6:cx=3:cy=3:ca=0.3"
_DEBAND_FILTER = "deband=1:64:16:16"


def _denoise_filter(denoise: str) -> str | None:
    try:
        return _DENOISE_FILTERS[denoise]
    except KeyError:
        raise ValueError(
            f"Unknown denoise level '{denoise}'. "
            f"Supported: {sorted(k for k in _DENOISE_FILTERS)}"
        ) from None


def _scale_filter(target_w: int, target_h: int) -> str:
    if not isinstance(target_w, int) or not isinstance(target_h, int):
        raise ValueError("target_w and target_h must be integers")
    if target_w <= 0 or target_h <= 0:
        raise ValueError("target_w and target_h must be positive")
    if target_w % 2 != 0 or target_h % 2 != 0:
        raise ValueError(
            "target_w and target_h must be even "
            "(required by 4:2:0 chroma subsampling)"
        )
    return (
        f"scale={target_w}:{target_h}:"
        "flags=lanczos+accurate_rnd+full_chroma_int+full_chroma_inp"
    )


def build_filter_chain(
    target_w: int,
    target_h: int,
    denoise: str = "gentle",
    sharpen: bool = True,
    deband: bool = False,
) -> str:
    """Build the ffmpeg video filter chain for upscaling.

    Args:
        target_w: Target width in pixels (positive, even).
        target_h: Target height in pixels (positive, even).
        denoise: One of "none" | "gentle" | "medium" | "strong".
        sharpen: Append the unsharp detail-restoration filter.
        deband: Append the gradient-debanding filter.

    Returns:
        Comma-joined filter chain string (video filters only), usable
        directly with ffmpeg's `-vf` option.

    Raises:
        ValueError: On unknown denoise level or invalid target dimensions.
    """
    stages: List[str] = []
    denoise_filter = _denoise_filter(denoise)
    if denoise_filter is not None:
        stages.append(denoise_filter)
    stages.append(_scale_filter(target_w, target_h))
    if sharpen:
        stages.append(_SHARPEN_FILTER)
    if deband:
        stages.append(_DEBAND_FILTER)
    return ",".join(stages)
