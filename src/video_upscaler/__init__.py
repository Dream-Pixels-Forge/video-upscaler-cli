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
from video_upscaler.engines import (
    BaseEngine,
    EngineUnavailableError,
    FFmpegPrecisionEngine,
    ProgressReporter,
    RealESRGANEngine,
    UpscaleConfig,
    UpscaleError,
    UpscaleResult,
    Upscaler,
)

__version__ = "0.1.2"

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
    "BaseEngine",
    "EngineUnavailableError",
    "FFmpegPrecisionEngine",
    "ProgressReporter",
    "RealESRGANEngine",
    "UpscaleConfig",
    "UpscaleError",
    "UpscaleResult",
    "Upscaler",
]
