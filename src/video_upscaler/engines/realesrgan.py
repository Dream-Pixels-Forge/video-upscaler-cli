"""Real-ESRGAN (ncnn-vulkan) engine adapter."""

import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional, Union

from video_upscaler.core.probe import VideoProbe

from video_upscaler.engines.base import (
    BaseEngine,
    EngineUnavailableError,
    UpscaleConfig,
    UpscaleResult,
)

BINARY = "realesrgan-ncnn-vulkan"


class RealESRGANEngine(BaseEngine):
    """Thin adapter around the realesrgan-ncnn-vulkan binary."""

    def __init__(self, config: UpscaleConfig) -> None:
        self.config = config

    @staticmethod
    def is_available() -> bool:
        return shutil.which(BINARY) is not None

    def upscale(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> UpscaleResult:
        if not self.is_available():
            raise EngineUnavailableError(
                f"'{BINARY}' not found on PATH. Install it or use the ffmpeg precision engine."
            )
        subprocess.run([BINARY, "-i", str(input_path), "-o", str(output_path)], check=True)
        info = VideoProbe.probe(output_path)
        return UpscaleResult(
            output_path=Path(output_path),
            width=info.width,
            height=info.height,
            duration=info.duration,
            input_path=Path(input_path),
        )
