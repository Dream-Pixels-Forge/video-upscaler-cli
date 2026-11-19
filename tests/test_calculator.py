import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from video_upscaler.core.types import (
    FitStrategy,
    LowResolutionError,
    Preset,
    TargetResolution,
)
from video_upscaler.core.calculator import ResolutionCalculator


class TestResolutionCalculator(unittest.TestCase):
    def test_minimum_resolution_validation_raises(self):
        """Input below 360p should raise LowResolutionError unless allow_low_res=True."""
        # 320x240 is 240p (< 360p)
        with self.assertRaises(LowResolutionError):
            ResolutionCalculator.calculate_target_resolution(320, 240, preset=Preset.RES_720P)

        # 400x300 is below 360p
        with self.assertRaises(LowResolutionError):
            ResolutionCalculator.calculate_target_resolution(400, 300, preset=Preset.RES_1080P)

        # 240x320 vertical is below 360p
        with self.assertRaises(LowResolutionError):
            ResolutionCalculator.calculate_target_resolution(240, 320, preset=Preset.RES_720P)

    def test_minimum_resolution_validation_override(self):
        """Low resolution input should be accepted if allow_low_res=True."""
        res = ResolutionCalculator.calculate_target_resolution(
            320, 240, preset=Preset.RES_720P, allow_low_res=True
        )
        self.assertIsInstance(res, TargetResolution)
        self.assertEqual(res.height, 720)
        self.assertEqual(res.width, 960)

    def test_presets_16_9(self):
        """Test presets 720p, 1080p, and 2k with standard 16:9 input (640x360)."""
        # 720p
        res_720 = ResolutionCalculator.calculate_target_resolution(640, 360, preset=Preset.RES_720P)
        self.assertEqual((res_720.width, res_720.height), (1280, 720))

        # 1080p
        res_1080 = ResolutionCalculator.calculate_target_resolution(640, 360, preset=Preset.RES_1080P)
        self.assertEqual((res_1080.width, res_1080.height), (1920, 1080))

        # 2k
        res_2k = ResolutionCalculator.calculate_target_resolution(640, 360, preset=Preset.RES_2K)
        self.assertEqual((res_2k.width, res_2k.height), (2560, 1440))

    def test_string_presets_accepted(self):
        """Presets can be passed as strings ('720p', '1080p', '2k')."""
        res = ResolutionCalculator.calculate_target_resolution(640, 360, preset="1080p")
        self.assertEqual((res.width, res.height), (1920, 1080))

    def test_scale_factor(self):
        """Custom scale factor like 2x, 1.5x."""
        res_2x = ResolutionCalculator.calculate_target_resolution(640, 360, scale_factor=2.0)
        self.assertEqual((res_2x.width, res_2x.height), (1280, 720))

        res_1_5x = ResolutionCalculator.calculate_target_resolution(640, 360, scale_factor=1.5)
        self.assertEqual((res_1_5x.width, res_1_5x.height), (960, 540))

    def test_even_dimensions_invariant(self):
        """Ensure all calculated resolutions produce strictly even dimensions."""
        test_inputs = [
            (641, 361),
            (853, 480),
            (711, 400),
            (640, 360),
            (1920, 1080),
        ]
        for w, h in test_inputs:
            for preset in [Preset.RES_720P, Preset.RES_1080P, Preset.RES_2K]:
                res = ResolutionCalculator.calculate_target_resolution(
                    w, h, preset=preset, allow_low_res=True
                )
                self.assertEqual(res.width % 2, 0, f"Width {res.width} is odd for input {w}x{h}")
                self.assertEqual(res.height % 2, 0, f"Height {res.height} is odd for input {w}x{h}")

    def test_aspect_ratios_handling(self):
        """Test 4:3, 21:9, and vertical 9:16 videos."""
        # 4:3 (640x480)
        res_4_3 = ResolutionCalculator.calculate_target_resolution(640, 480, preset=Preset.RES_1080P)
        self.assertEqual((res_4_3.width, res_4_3.height), (1440, 1080))

        # 21:9 (840x360)
        res_21_9 = ResolutionCalculator.calculate_target_resolution(840, 360, preset=Preset.RES_1080P)
        self.assertEqual((res_21_9.width, res_21_9.height), (2520, 1080))

        # 9:16 vertical (360x640)
        res_vert = ResolutionCalculator.calculate_target_resolution(360, 640, preset=Preset.RES_1080P)
        self.assertEqual((res_vert.width, res_vert.height), (1080, 1920))

        res_vert_720 = ResolutionCalculator.calculate_target_resolution(360, 640, preset=Preset.RES_720P)
        self.assertEqual((res_vert_720.width, res_vert_720.height), (720, 1280))

        res_vert_2k = ResolutionCalculator.calculate_target_resolution(360, 640, preset=Preset.RES_2K)
        self.assertEqual((res_vert_2k.width, res_vert_2k.height), (1440, 2560))

    def test_fit_strategy_fit(self):
        """FitStrategy.FIT preserves AR with no padding or cropping."""
        res = ResolutionCalculator.calculate_target_resolution(
            480, 360, preset=Preset.RES_1080P, fit_strategy=FitStrategy.FIT
        )
        self.assertEqual((res.width, res.height), (1440, 1080))
        self.assertEqual((res.scaled_width, res.scaled_height), (1440, 1080))
        self.assertEqual(res.pad_x, 0)
        self.assertEqual(res.pad_y, 0)
        self.assertEqual(res.crop_w, 0)
        self.assertEqual(res.crop_h, 0)

    def test_fit_strategy_pad(self):
        """FitStrategy.PAD fits video into canvas and pads remaining space (pillarbox/letterbox)."""
        # 4:3 video (480x360) into 1080p canvas (1920x1080) -> pillarbox
        res_pad = ResolutionCalculator.calculate_target_resolution(
            480, 360, preset=Preset.RES_1080P, fit_strategy=FitStrategy.PAD
        )
        self.assertEqual((res_pad.width, res_pad.height), (1920, 1080))
        self.assertEqual((res_pad.scaled_width, res_pad.scaled_height), (1440, 1080))
        self.assertEqual(res_pad.pad_x, 240)
        self.assertEqual(res_pad.pad_y, 0)
        self.assertEqual(res_pad.pad_x % 2, 0)
        self.assertEqual(res_pad.pad_y % 2, 0)

        # 21:9 video (840x360) into 1080p canvas (1920x1080) -> letterbox
        res_letterbox = ResolutionCalculator.calculate_target_resolution(
            840, 360, preset=Preset.RES_1080P, fit_strategy=FitStrategy.PAD
        )
        self.assertEqual((res_letterbox.width, res_letterbox.height), (1920, 1080))
        self.assertEqual(res_letterbox.scaled_width, 1920)
        self.assertTrue(res_letterbox.scaled_height < 1080)
        self.assertTrue(res_letterbox.pad_y > 0)
        self.assertEqual(res_letterbox.pad_y % 2, 0)

    def test_fit_strategy_crop(self):
        """FitStrategy.CROP scales video to fill canvas and crops overflow."""
        # 4:3 video (480x360) into 1080p canvas (1920x1080)
        res_crop = ResolutionCalculator.calculate_target_resolution(
            480, 360, preset=Preset.RES_1080P, fit_strategy=FitStrategy.CROP
        )
        self.assertEqual((res_crop.width, res_crop.height), (1920, 1080))
        self.assertEqual(res_crop.scaled_width, 1920)
        self.assertEqual(res_crop.scaled_height, 1440)
        self.assertEqual(res_crop.crop_w, 1920)
        self.assertEqual(res_crop.crop_h, 1080)
        self.assertEqual(res_crop.crop_x, 0)
        self.assertEqual(res_crop.crop_y, 180)
        self.assertEqual(res_crop.crop_y % 2, 0)

    def test_custom_dimensions(self):
        """Custom dimensions with custom_w and custom_h."""
        res = ResolutionCalculator.calculate_target_resolution(
            640, 360, custom_w=1920, custom_h=800, fit_strategy=FitStrategy.FIT
        )
        self.assertEqual((res.width, res.height), (1920, 800))

    def test_tuple_unpacking(self):
        """TargetResolution can be unpacked directly as (w, h)."""
        w, h = ResolutionCalculator.calculate_target_resolution(640, 360, preset=Preset.RES_720P)
        self.assertEqual(w, 1280)
        self.assertEqual(h, 720)


if __name__ == "__main__":
    unittest.main()
