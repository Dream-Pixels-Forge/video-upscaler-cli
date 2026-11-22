"""Base engine contract, shared config/result types, and engine exceptions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple, Union

from video_upscaler.core.types import DenoiseLevel, FitStrategy, Preset, QualityProfile


class EngineUnavailableError(RuntimeError):
    """Raised when an engine's required external binary is not available."""


class UpscaleError(RuntimeError):
    """Raised when the upscale subprocess fails."""


@dataclass
class UpscaleConfig:
    """User-facing configuration for an upscale run."""

    preset: Preset = Preset.RES_1080P
    fit: FitStrategy = FitStrategy.FIT
    quality: QualityProfile = QualityProfile.MEDIUM
    denoise: DenoiseLevel = DenoiseLevel.GENTLE
    sharpen: bool = True
    deband: bool = False
    codec: str = "libx264"
    allow_low_res: bool = False
    scale_factor: Optional[float] = None
    custom_w: Optional[int] = None
    custom_h: Optional[int] = None
    dci: bool = False


@dataclass
class UpscaleResult:
    """Outcome of a successful upscale run."""

    output_path: Path
    width: int
    height: int
    duration: float
    input_path: Path

    @property
    def resolution(self) -> Tuple[int, int]:
        return (self.width, self.height)


class BaseEngine(ABC):
    """Common interface for upscale engines."""

    @abstractmethod
    def upscale(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> UpscaleResult:
        """Upscale input_path into output_path, reporting progress as (percent, message)."""
