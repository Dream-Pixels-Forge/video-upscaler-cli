"""video_upscaler - High-precision video upscaling CLI and library."""

from video_upscaler.core import (
    DenoiseLevel,
    FitStrategy,
    LowResolutionError,
    Preset,
    ProbeError,
    QualityProfile,
    ResolutionCalculator,
    TargetResolution,
    VideoInfo,
    VideoProbe,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Preset",
    "FitStrategy",
    "QualityProfile",
    "DenoiseLevel",
    "LowResolutionError",
    "ProbeError",
    "VideoInfo",
    "TargetResolution",
    "ResolutionCalculator",
    "VideoProbe",
]
