"""Data types, Enums, and exceptions for video_upscaler core."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional, Tuple


class Preset(str, Enum):
    """Standard target resolution presets."""
    RES_720P = "720p"
    RES_1080P = "1080p"
    RES_2K = "2k"
    RES_DCI_2K = "dci_2k"
    CUSTOM = "custom"

    @classmethod
    def from_str(cls, value: str) -> "Preset":
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized or member.name.lower() == normalized:
                return member
        raise ValueError(f"Unknown preset '{value}'. Supported: {[p.value for p in cls]}")


class FitStrategy(str, Enum):
    """Strategy for fitting source video into target bounding box or canvas."""
    FIT = "fit"
    PAD = "pad"
    CROP = "crop"

    @classmethod
    def from_str(cls, value: str) -> "FitStrategy":
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized or member.name.lower() == normalized:
                return member
        raise ValueError(f"Unknown fit strategy '{value}'. Supported: {[f.value for f in cls]}")


class QualityProfile(str, Enum):
    """Quality and speed trade-off profiles."""
    FAST = "fast"
    MEDIUM = "medium"
    HIGH = "high"
    BEST = "best"


class DenoiseLevel(str, Enum):
    """Denoise filtering intensity."""
    NONE = "none"
    GENTLE = "gentle"
    MEDIUM = "medium"
    STRONG = "strong"


class LowResolutionError(ValueError):
    """Raised when input video resolution is below minimum allowed threshold (360p)."""
    pass


class ProbeError(RuntimeError):
    """Raised when probing video metadata fails or media contains no video stream."""
    pass


@dataclass
class VideoInfo:
    """Metadata container for a probed video file."""
    path: Path
    width: int
    height: int
    duration: float
    fps: float
    codec: str
    pix_fmt: str
    bitrate: Optional[int] = None
    audio_codec: Optional[str] = None
    audio_channels: Optional[int] = None
    aspect_ratio: Optional[str] = None
    color_space: Optional[str] = None
    total_frames: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            self.path = Path(self.path)

    @property
    def is_vertical(self) -> bool:
        """True if height is strictly greater than width (portrait orientation)."""
        return self.height > self.width

    @property
    def aspect_ratio_float(self) -> float:
        """Aspect ratio as float (width / height)."""
        return self.width / self.height if self.height else 0.0

    @property
    def resolution(self) -> Tuple[int, int]:
        """(width, height) tuple."""
        return (self.width, self.height)


@dataclass(frozen=True)
class TargetResolution:
    """Calculated target resolution and transformation parameters."""
    width: int
    height: int
    scaled_width: int
    scaled_height: int
    pad_x: int = 0
    pad_y: int = 0
    crop_x: int = 0
    crop_y: int = 0
    crop_w: int = 0
    crop_h: int = 0

    def __iter__(self) -> Iterator[int]:
        """Allow tuple unpacking (w, h) = target_resolution."""
        yield self.width
        yield self.height

    @property
    def is_padded(self) -> bool:
        return self.pad_x > 0 or self.pad_y > 0

    @property
    def is_cropped(self) -> bool:
        return self.crop_w > 0 and (self.crop_w < self.scaled_width or self.crop_h < self.scaled_height)
