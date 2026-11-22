"""FFmpeg precision upscale engine."""

import subprocess
from pathlib import Path
from typing import Callable, List, Optional, Union

from video_upscaler.core.calculator import ResolutionCalculator
from video_upscaler.core.probe import VideoProbe
from video_upscaler.core.types import QualityProfile, VideoInfo

from video_upscaler.engines.base import (
    BaseEngine,
    UpscaleConfig,
    UpscaleError,
    UpscaleResult,
)
from video_upscaler.engines.progress import ProgressReporter

# QualityProfile -> (x264 preset, CRF)
_QUALITY_MAP = {
    QualityProfile.FAST.value: ("veryfast", 20),
    QualityProfile.MEDIUM.value: ("medium", 18),
    QualityProfile.HIGH.value: ("slow", 16),
    QualityProfile.BEST.value: ("slower", 14),
}

FilterChainFn = Callable[..., str]


def _default_filter_chain_fn(
    target_w: int,
    target_h: int,
    denoise: str = "gentle",
    sharpen: bool = True,
    deband: bool = False,
) -> str:
    # Lazy import: filters.chain may be delivered by a parallel workstream.
    from video_upscaler.filters.chain import build_filter_chain

    return build_filter_chain(target_w, target_h, denoise=denoise, sharpen=sharpen, deband=deband)


class FFmpegPrecisionEngine(BaseEngine):
    """Upscales video via a single ffmpeg invocation with precision filters."""

    def __init__(self, config: UpscaleConfig, filter_chain_fn: Optional[FilterChainFn] = None) -> None:
        self.config = config
        self._filter_chain_fn = filter_chain_fn

    def build_command(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        video_info: VideoInfo,
        chain: str,
    ) -> List[str]:
        """Assemble the full ffmpeg argument list from config, probe info, and -vf chain."""
        x264_preset, crf = _QUALITY_MAP[QualityProfile(self.config.quality).value]
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vf",
            chain,
            "-c:v",
            self.config.codec,
            "-preset",
            x264_preset,
            "-crf",
            str(crf),
        ]
        if video_info.audio_codec is not None:
            cmd += ["-c:a", "copy"]
        cmd += ["-pix_fmt", "yuv420p", str(output_path)]
        return cmd

    def upscale(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> UpscaleResult:
        info = VideoProbe.probe(input_path)
        # LowResolutionError propagates from here unless config.allow_low_res.
        target = ResolutionCalculator.calculate_target_resolution(
            source_w=info.width,
            source_h=info.height,
            preset=self.config.preset,
            fit_strategy=self.config.fit,
            custom_w=self.config.custom_w,
            custom_h=self.config.custom_h,
            scale_factor=self.config.scale_factor,
            allow_low_res=self.config.allow_low_res,
            dci=self.config.dci,
        )
        chain_fn = self._filter_chain_fn or _default_filter_chain_fn
        chain = chain_fn(
            target.width,
            target.height,
            denoise=self.config.denoise.value,
            sharpen=self.config.sharpen,
            deband=self.config.deband,
        )
        cmd = self.build_command(input_path, output_path, info, chain)

        reporter = ProgressReporter(info.duration, progress_callback)
        stderr_lines: List[str] = []
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        for line in proc.stderr:
            stderr_lines.append(line)
            reporter.report(line)
        if proc.wait() != 0:
            tail = "".join(stderr_lines[-5:]).strip()
            raise UpscaleError(f"ffmpeg failed with exit code {proc.returncode}: {tail}")

        return UpscaleResult(
            output_path=Path(output_path),
            width=target.width,
            height=target.height,
            duration=info.duration,
            input_path=Path(input_path),
        )
