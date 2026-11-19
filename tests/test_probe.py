import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from video_upscaler.core.probe import VideoProbe
from video_upscaler.core.types import ProbeError, VideoInfo


SAMPLE_FFPROBE_OUTPUT = {
    "streams": [
        {
            "index": 0,
            "codec_name": "h264",
            "codec_type": "video",
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "30000/1001",
            "avg_frame_rate": "30000/1001",
            "pix_fmt": "yuv420p",
            "color_space": "bt709",
            "duration": "12.500000",
            "bit_rate": "4500000",
            "nb_frames": "375",
            "display_aspect_ratio": "16:9",
        },
        {
            "index": 1,
            "codec_name": "aac",
            "codec_type": "audio",
            "channels": 2,
            "sample_rate": "48000",
        },
    ],
    "format": {
        "filename": "sample.mp4",
        "nb_streams": 2,
        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        "duration": "12.500000",
        "size": "7031250",
        "bit_rate": "4500000",
    },
}


class TestVideoProbe(unittest.TestCase):
    def test_parse_probe_json_with_audio(self):
        """Test parsing valid ffprobe JSON with video and audio streams."""
        info = VideoProbe.parse_probe_json(SAMPLE_FFPROBE_OUTPUT, path=Path("sample.mp4"))

        self.assertIsInstance(info, VideoInfo)
        self.assertEqual(info.width, 1920)
        self.assertEqual(info.height, 1080)
        self.assertEqual(info.codec, "h264")
        self.assertEqual(info.pix_fmt, "yuv420p")
        self.assertAlmostEqual(info.fps, 29.97003, places=4)
        self.assertAlmostEqual(info.duration, 12.5)
        self.assertEqual(info.bitrate, 4500000)
        self.assertEqual(info.audio_codec, "aac")
        self.assertEqual(info.audio_channels, 2)
        self.assertEqual(info.aspect_ratio, "16:9")
        self.assertEqual(info.color_space, "bt709")
        self.assertEqual(info.total_frames, 375)
        self.assertFalse(info.is_vertical)
        self.assertEqual(info.resolution, (1920, 1080))

    def test_parse_probe_json_video_only(self):
        """Test parsing video without audio stream."""
        raw = {
            "streams": [
                {
                    "codec_name": "vp9",
                    "codec_type": "video",
                    "width": 640,
                    "height": 360,
                    "r_frame_rate": "24/1",
                    "pix_fmt": "yuv420p",
                    "duration": "5.0",
                }
            ],
            "format": {"duration": "5.0"},
        }
        info = VideoProbe.parse_probe_json(raw, path=Path("silent.webm"))
        self.assertEqual(info.codec, "vp9")
        self.assertEqual(info.width, 640)
        self.assertEqual(info.height, 360)
        self.assertIsNone(info.audio_codec)
        self.assertIsNone(info.audio_channels)
        self.assertEqual(info.fps, 24.0)

    def test_vertical_video_detection(self):
        """Vertical (portrait) video detection."""
        raw = {
            "streams": [
                {
                    "codec_name": "h264",
                    "codec_type": "video",
                    "width": 1080,
                    "height": 1920,
                    "r_frame_rate": "60/1",
                    "pix_fmt": "yuv420p",
                    "duration": "10.0",
                }
            ],
            "format": {"duration": "10.0"},
        }
        info = VideoProbe.parse_probe_json(raw)
        self.assertTrue(info.is_vertical)
        self.assertAlmostEqual(info.aspect_ratio_float, 1080 / 1920)

    def test_fps_parsing_edge_cases(self):
        """Verify frame rate parsing for fractional, invalid, and standard formats."""
        self.assertAlmostEqual(VideoProbe._parse_fps("24/1"), 24.0)
        self.assertAlmostEqual(VideoProbe._parse_fps("30000/1001"), 29.97003, places=4)
        self.assertAlmostEqual(VideoProbe._parse_fps("60/1"), 60.0)
        self.assertEqual(VideoProbe._parse_fps("0/0"), 0.0)
        self.assertEqual(VideoProbe._parse_fps("invalid"), 0.0)
        self.assertEqual(VideoProbe._parse_fps(None), 0.0)

    def test_probe_missing_file_raises(self):
        """Probing non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            VideoProbe.probe(Path("/nonexistent/video.mp4"))

    def test_probe_no_video_stream_raises(self):
        """Media file without video stream raises ProbeError."""
        audio_only = {
            "streams": [
                {
                    "codec_name": "mp3",
                    "codec_type": "audio",
                    "channels": 2,
                }
            ],
            "format": {},
        }
        with self.assertRaises(ProbeError):
            VideoProbe.parse_probe_json(audio_only)

    def test_probe_corrupt_json_raises(self):
        """Invalid JSON output raises ProbeError."""
        with self.assertRaises(ProbeError):
            VideoProbe.parse_probe_json("not valid json")

    @patch("subprocess.run")
    def test_probe_subprocess_invoked_securely(self, mock_run):
        """Ensure ffprobe is called with argv list, never shell=True."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(SAMPLE_FFPROBE_OUTPUT)
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.is_file", return_value=True):
            info = VideoProbe.probe("test.mp4")

        self.assertIsInstance(info, VideoInfo)
        self.assertEqual(info.width, 1920)

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        self.assertIsInstance(cmd, list)
        self.assertEqual(cmd[0], "ffprobe")
        self.assertFalse(kwargs.get("shell", False))

    @patch("subprocess.run")
    def test_probe_subprocess_failure_raises_probe_error(self, mock_run):
        """When ffprobe exits with non-zero code, raise ProbeError."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "Invalid data found when processing input"
        mock_run.return_value = mock_proc

        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.is_file", return_value=True):
            with self.assertRaises(ProbeError) as ctx:
                VideoProbe.probe("bad_file.mp4")
            self.assertIn("ffprobe failed", str(ctx.exception))

    def test_probe_real_video_file(self):
        """Test probing an actual generated synthetic MP4 video using real ffprobe."""
        import tempfile
        import shutil

        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg or ffprobe not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "synth_360p.mp4"
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "lavfi",
                "-i", "testsrc=duration=0.5:size=640x360:rate=24",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                str(test_file),
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            info = VideoProbe.probe(test_file)
            self.assertEqual(info.width, 640)
            self.assertEqual(info.height, 360)
            self.assertAlmostEqual(info.fps, 24.0, places=1)
            self.assertEqual(info.codec, "h264")
            self.assertEqual(info.pix_fmt, "yuv420p")
            self.assertFalse(info.is_vertical)
            self.assertGreater(info.duration, 0.4)



if __name__ == "__main__":
    unittest.main()
