"""Precision filter chain builders for the FFmpeg upscale engine.

Assembles a single `-vf` filtergraph string from the SPEC pipeline:

    1. Denoise (optional)      -> hqdn3d
    2. Precision scaler        -> scale=w:h:flags=lanczos+accurate_rnd+full_chroma_int+full_chroma_inp
    3. Detail & edge restoration -> unsharp
    4. Debanding (optional)    -> deband
"""

from video_upscaler.core.types import DenoiseLevel

# DenoiseLevel -> hqdn3d parameters (ltr: luma_spatial, luma_temp, chroma_spatial, chroma_temp)
_DENOISE_PARAMS = {
    DenoiseLevel.NONE: None,
    DenoiseLevel.GENTLE: "1.5:1.5:3:3",
    DenoiseLevel.MEDIUM: "3:3:5:5",
    DenoiseLevel.STRONG: "5:5:7:7",
}

_SHARPEN = "unsharp=lx=5:ly=5:la=0.6:cx=3:cy=3:ca=0.3"
_DEBAND = "deband=1:64:16:16"
_SCALE_FLAGS = "lanczos+accurate_rnd+full_chroma_int+full_chroma_inp"


def build_filter_chain(
    target_w: int,
    target_h: int,
    denoise: str = "gentle",
    sharpen: bool = True,
    deband: bool = False,
) -> str:
    """Build an ffmpeg `-vf` filter chain for precision upscaling.

    Args:
        target_h: Target output height.
        target_w: Target output width.
        denoise: Denoise level name ('none', 'gentle', 'medium', 'strong').
        sharpen: Whether to include the unsharp sharpening filter.
        deband: Whether to include the debanding filter.

    Returns:
        A comma-separated filtergraph string ready for ffmpeg `-vf`.
    """
    filters: list[str] = []

    level = DenoiseLevel(denoise.strip().lower())
    params = _DENOISE_PARAMS[level]
    if params is not None:
        filters.append(f"hqdn3d={params}")

    filters.append(f"scale={target_w}:{target_h}:flags={_SCALE_FLAGS}")

    if sharpen:
        filters.append(_SHARPEN)

    if deband:
        filters.append(_DEBAND)

    return ",".join(filters)
