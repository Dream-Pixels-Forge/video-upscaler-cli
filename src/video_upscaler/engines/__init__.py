"""Upscale engines and public upscaler API."""

from video_upscaler.engines.base import (
    BaseEngine,
    EngineUnavailableError,
    UpscaleConfig,
    UpscaleError,
    UpscaleResult,
)
from video_upscaler.engines.ffmpeg import FFmpegPrecisionEngine
from video_upscaler.engines.progress import ProgressReporter
from video_upscaler.engines.realesrgan import RealESRGANEngine

# Public facade: the ffmpeg precision engine is the default upscaler.
Upscaler = FFmpegPrecisionEngine

__all__ = [
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
