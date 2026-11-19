"""FFprobe metadata extraction and media inspection."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Union

from video_upscaler.core.types import ProbeError, VideoInfo


class VideoProbe:
    """Probes media files using ffprobe to extract stream, codec, and timing metadata."""

    @classmethod
    def probe(cls, path: Union[str, Path]) -> VideoInfo:
        """Probe a video file on disk using ffprobe.

        Args:
            path: Path to the media file.

        Returns:
            VideoInfo with extracted streams, codec, resolution, and timing metadata.

        Raises:
            FileNotFoundError: If the media file does not exist.
            ProbeError: If ffprobe fails, produces invalid output, or no video stream exists.
        """
        p = Path(path).resolve()
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Media file not found: {path}")

        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(p),
        ]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                shell=False,
            )
        except FileNotFoundError:
            raise ProbeError("ffprobe executable not found on system PATH. Please ensure ffmpeg is installed.")
        except Exception as e:
            raise ProbeError(f"Failed to execute ffprobe: {e}") from e

        if proc.returncode != 0:
            err = proc.stderr.strip() or f"ffprobe exited with status {proc.returncode}"
            raise ProbeError(f"ffprobe failed for {p}: {err}")

        return cls.parse_probe_json(proc.stdout, path=p)

    @classmethod
    def parse_probe_json(
        cls,
        data: Union[str, Dict[str, Any]],
        path: Optional[Union[str, Path]] = None,
    ) -> VideoInfo:
        """Parse raw ffprobe JSON output into a VideoInfo dataclass.

        Args:
            data: Raw JSON string or deserialized dict from ffprobe.
            path: Optional file path to associate with the VideoInfo.

        Returns:
            VideoInfo dataclass.

        Raises:
            ProbeError: If JSON is invalid or no video stream is present.
        """
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception as e:
                raise ProbeError(f"Invalid ffprobe JSON output: {e}") from e

        if not isinstance(data, dict):
            raise ProbeError("Malformed probe data: expected JSON object")

        streams = data.get("streams", [])
        video_stream: Optional[Dict[str, Any]] = None
        audio_stream: Optional[Dict[str, Any]] = None

        for stream in streams:
            codec_type = stream.get("codec_type")
            if codec_type == "video" and video_stream is None:
                video_stream = stream
            elif codec_type == "audio" and audio_stream is None:
                audio_stream = stream

        if video_stream is None:
            raise ProbeError(f"No video stream found in media file: {path or 'unknown'}")

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        codec = str(video_stream.get("codec_name", "unknown"))
        pix_fmt = str(video_stream.get("pix_fmt", "unknown"))

        # Frame rate parsing
        fps = cls._parse_fps(video_stream.get("r_frame_rate"))
        if fps == 0.0:
            fps = cls._parse_fps(video_stream.get("avg_frame_rate"))

        # Duration parsing
        duration_raw = video_stream.get("duration") or data.get("format", {}).get("duration")
        try:
            duration = float(duration_raw) if duration_raw is not None else 0.0
        except (ValueError, TypeError):
            duration = 0.0

        # Bitrate parsing
        bitrate_raw = video_stream.get("bit_rate") or data.get("format", {}).get("bit_rate")
        try:
            bitrate = int(bitrate_raw) if bitrate_raw is not None else None
        except (ValueError, TypeError):
            bitrate = None

        aspect_ratio = video_stream.get("display_aspect_ratio")
        color_space = video_stream.get("color_space")

        # Total frames parsing
        nb_frames_raw = video_stream.get("nb_frames")
        try:
            total_frames = int(nb_frames_raw) if nb_frames_raw is not None else None
        except (ValueError, TypeError):
            total_frames = None

        # Audio stream info
        audio_codec = None
        audio_channels = None
        if audio_stream is not None:
            audio_codec = audio_stream.get("codec_name")
            try:
                audio_channels = int(audio_stream["channels"]) if "channels" in audio_stream else None
            except (ValueError, TypeError):
                audio_channels = None

        media_path = Path(path) if path else Path(data.get("format", {}).get("filename", "unknown"))

        return VideoInfo(
            path=media_path,
            width=width,
            height=height,
            duration=duration,
            fps=fps,
            codec=codec,
            pix_fmt=pix_fmt,
            bitrate=bitrate,
            audio_codec=audio_codec,
            audio_channels=audio_channels,
            aspect_ratio=aspect_ratio,
            color_space=color_space,
            total_frames=total_frames,
        )

    @staticmethod
    def _parse_fps(fps_val: Optional[Union[str, float, int]]) -> float:
        """Parse fractional or float fps strings (e.g. '30000/1001', '24/1', '29.97')."""
        if not fps_val:
            return 0.0
        if isinstance(fps_val, (int, float)):
            return float(fps_val)
        fps_str = str(fps_val).strip()
        try:
            if "/" in fps_str:
                num_str, den_str = fps_str.split("/", 1)
                num = float(num_str)
                den = float(den_str)
                return (num / den) if den != 0.0 else 0.0
            return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return 0.0
