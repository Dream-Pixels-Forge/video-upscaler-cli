"""Tests for the upscale engine API: config, command assembly, progress, results.

No real ffmpeg/ffprobe is ever executed — subprocess and probing are mocked.
"""

from pathlib import Path

import pytest

from video_upscaler import (
    DenoiseLevel,
    FitStrategy,
    LowResolutionError,
    Preset,
    QualityProfile,
    VideoInfo,
)
from video_upscaler.engines import (
    EngineUnavailableError,
    ProgressReporter,
    RealESRGANEngine,
    UpscaleConfig,
    UpscaleResult,
    Upscaler,
)
from video_upscaler.engines.ffmpeg import FFmpegPrecisionEngine


def make_info(w=640, h=480, duration=30.0, audio_codec="aac") -> VideoInfo:
    return VideoInfo(
        path=Path("fake_input.mp4"),
        width=w,
        height=h,
        duration=duration,
        fps=30.0,
        codec="h264",
        pix_fmt="yuv420p",
        audio_codec=audio_codec,
    )


class FakePopen:
    """Stands in for subprocess.Popen; replays canned stderr lines."""

    stderr_lines = [
        "ffmpeg version 6.0 Copyright (c) 2000-2023 the FFmpeg developers",
        "frame=   25 fps=0.0 q=28.0 size=     256kB time=00:00:01.00 bitrate=2097.1kbits/s",
        "frame=  300 fps=25 q=28.0 size=    1024kB time=00:00:12.00 bitrate=699.1kbits/s speed=2x",
    ]

    def __init__(self, cmd, **kwargs):
        self.cmd = cmd
        self.kwargs = kwargs
        self.stderr = iter(list(self.stderr_lines))
        self.returncode = 0

    def wait(self):
        return self.returncode


@pytest.fixture
def patched_probe(monkeypatch):
    def _patch(info):
        monkeypatch.setattr(
            "video_upscaler.engines.ffmpeg.VideoProbe.probe",
            staticmethod(lambda path: info),
        )
        return info

    return _patch


@pytest.fixture
def patched_popen(monkeypatch):
    spawned = []

    def _factory(lines=None, returncode=0):
        class _Popen(FakePopen):
            def __init__(self, cmd, **kwargs):
                super().__init__(cmd, **kwargs)
                if lines is not None:
                    self.stderr = iter(list(lines))
                self.returncode = returncode

        monkeypatch.setattr("video_upscaler.engines.ffmpeg.subprocess.Popen", _Popen)
        return _Popen

    def _spawn(lines=None, returncode=0):
        cls = _factory(lines, returncode)

        def recorder(cmd, **kwargs):
            spawned.append(cmd)
            return cls(cmd, **kwargs)

        monkeypatch.setattr("video_upscaler.engines.ffmpeg.subprocess.Popen", recorder)
        return spawned

    return _spawn


# ---------------------------------------------------------------------------
# UpscaleConfig
# ---------------------------------------------------------------------------


class TestUpscaleConfig:
    def test_defaults(self):
        cfg = UpscaleConfig()
        assert cfg.preset is Preset.RES_1080P
        assert cfg.fit is FitStrategy.FIT
        assert cfg.quality is QualityProfile.MEDIUM
        assert cfg.denoise is DenoiseLevel.GENTLE
        assert cfg.sharpen is True
        assert cfg.deband is False
        assert cfg.codec == "libx264"
        assert cfg.allow_low_res is False


# ---------------------------------------------------------------------------
# Command assembly
# ---------------------------------------------------------------------------


class TestBuildCommand:
    def test_exact_command_with_audio(self):
        engine = FFmpegPrecisionEngine(UpscaleConfig())
        cmd = engine.build_command(Path("in.mp4"), Path("out.mp4"), make_info(), "scale=1440:1080")
        assert cmd == [
            "ffmpeg",
            "-y",
            "-i",
            "in.mp4",
            "-vf",
            "scale=1440:1080",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "copy",
            "-pix_fmt",
            "yuv420p",
            "out.mp4",
        ]

    def test_no_audio_stream_omits_audio_args(self):
        engine = FFmpegPrecisionEngine(UpscaleConfig())
        cmd = engine.build_command(Path("in.mp4"), Path("out.mp4"), make_info(audio_codec=None), "scale")
        assert "-c:a" not in cmd
        assert "copy" not in cmd

    @pytest.mark.parametrize(
        "quality, x264_preset, crf",
        [
            ("fast", "veryfast", "20"),
            ("medium", "medium", "18"),
            ("high", "slow", "16"),
            ("best", "slower", "14"),
        ],
    )
    def test_quality_maps_to_x264_preset_and_crf(self, quality, x264_preset, crf):
        engine = FFmpegPrecisionEngine(UpscaleConfig(quality=QualityProfile(quality)))
        cmd = engine.build_command(Path("in.mp4"), Path("out.mp4"), make_info(), "scale")
        i = cmd.index("-preset")
        j = cmd.index("-crf")
        assert cmd[i + 1] == x264_preset
        assert cmd[j + 1] == crf

    def test_custom_codec(self):
        engine = FFmpegPrecisionEngine(UpscaleConfig(codec="libx265"))
        cmd = engine.build_command(Path("in.mp4"), Path("out.mp4"), make_info(), "scale")
        assert cmd[cmd.index("-c:v") + 1] == "libx265"


# ---------------------------------------------------------------------------
# upscale() flow (probe, calculator, subprocess all mocked)
# ---------------------------------------------------------------------------


class TestUpscaleFlow:
    def test_rejects_low_resolution_input(self, patched_probe):
        patched_probe(make_info(w=320, h=240))
        engine = FFmpegPrecisionEngine(UpscaleConfig())
        with pytest.raises(LowResolutionError):
            engine.upscale(Path("in.mp4"), Path("out.mp4"))

    def test_allow_low_res_bypasses_rejection(self, patched_probe, patched_popen):
        patched_probe(make_info(w=320, h=240))
        patched_popen()
        engine = FFmpegPrecisionEngine(UpscaleConfig(allow_low_res=True))
        result = engine.upscale(Path("in.mp4"), Path("out.mp4"))
        assert result.height == 1080

    def test_result_fields(self, patched_probe, patched_popen):
        patched_probe(make_info(w=640, h=480, duration=30.0))
        patched_popen()
        engine = FFmpegPrecisionEngine(UpscaleConfig())
        result = engine.upscale(Path("in.mp4"), Path("out.mp4"))
        assert isinstance(result, UpscaleResult)
        assert result.output_path == Path("out.mp4")
        assert result.input_path == Path("in.mp4")
        assert result.duration == 30.0
        # 640x480 fit into 1080p canvas: 4:3 -> 1440x1080
        assert result.width == 1440
        assert result.height == 1080
        assert result.resolution == (1440, 1080)

    def test_filter_chain_fn_injection(self, patched_probe, patched_popen):
        patched_probe(make_info())
        spawned = patched_popen()
        calls = []

        def fake_chain(w, h, denoise="gentle", sharpen=True, deband=False):
            calls.append((w, h, denoise, sharpen, deband))
            return f"scale={w}:{h}"

        engine = FFmpegPrecisionEngine(UpscaleConfig(), filter_chain_fn=fake_chain)
        engine.upscale(Path("in.mp4"), Path("out.mp4"))
        assert calls == [(1440, 1080, "gentle", True, False)]
        cmd = spawned[0]
        assert cmd[cmd.index("-vf") + 1] == "scale=1440:1080"

    def test_failed_process_raises(self, patched_probe, patched_popen):
        patched_probe(make_info())
        patched_popen(lines=["error: something broke"], returncode=1)
        from video_upscaler.engines import UpscaleError

        engine = FFmpegPrecisionEngine(UpscaleConfig())
        with pytest.raises(UpscaleError):
            engine.upscale(Path("in.mp4"), Path("out.mp4"))

    def test_upscaler_facade_matches_engine(self):
        assert Upscaler is FFmpegPrecisionEngine


# ---------------------------------------------------------------------------
# ProgressReporter
# ---------------------------------------------------------------------------


class TestProgressReporter:
    def test_parses_time_against_duration(self):
        seen = []
        reporter = ProgressReporter(30.0, lambda pct, msg: seen.append((pct, msg)))
        reporter.report("frame= 300 fps=25 time=00:00:12.00 bitrate=699.1kbits/s")
        pct, msg = seen[-1]
        assert pct == pytest.approx(40.0)
        assert isinstance(msg, str)

    def test_ignores_lines_without_time(self):
        seen = []
        reporter = ProgressReporter(30.0, lambda pct, msg: seen.append((pct, msg)))
        reporter.report("ffmpeg version 6.0 Copyright (c) 2000-2023")
        assert seen == []

    def test_clamps_over_100_percent(self):
        seen = []
        reporter = ProgressReporter(30.0, lambda pct, msg: seen.append(pct))
        reporter.report("time=01:00:00.00")
        assert seen[-1] == 100.0

    def test_no_callback_is_safe(self):
        reporter = ProgressReporter(30.0)
        reporter.report("time=00:00:12.00")

    def test_engine_streams_progress(self, patched_probe, patched_popen):
        patched_probe(make_info(duration=30.0))
        patched_popen()
        seen = []
        engine = FFmpegPrecisionEngine(UpscaleConfig())
        engine.upscale(Path("in.mp4"), Path("out.mp4"), progress_callback=lambda pct, msg: seen.append(pct))
        assert any(p == pytest.approx(40.0) for p in seen)


# ---------------------------------------------------------------------------
# RealESRGANEngine
# ---------------------------------------------------------------------------


class TestRealESRGANEngine:
    def test_unavailable_binary_raises(self, monkeypatch):
        monkeypatch.setattr("video_upscaler.engines.realesrgan.shutil.which", lambda name: None)
        engine = RealESRGANEngine(UpscaleConfig())
        assert engine.is_available() is False
        with pytest.raises(EngineUnavailableError):
            engine.upscale(Path("in.mp4"), Path("out.mp4"))

    def test_available_binary_detected(self, monkeypatch):
        monkeypatch.setattr(
            "video_upscaler.engines.realesrgan.shutil.which",
            lambda name: "/usr/bin/realesrgan-ncnn-vulkan",
        )
        engine = RealESRGANEngine(UpscaleConfig())
        assert engine.is_available() is True
