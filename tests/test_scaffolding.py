import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class TestScaffolding(unittest.TestCase):
    def test_version_and_imports(self):
        import video_upscaler
        self.assertTrue(hasattr(video_upscaler, "__version__"))
        self.assertIsInstance(video_upscaler.__version__, str)
        self.assertTrue(len(video_upscaler.__version__) > 0)

    def test_package_layout(self):
        import video_upscaler.core
        import video_upscaler.engines
        import video_upscaler.filters
        import video_upscaler.cli
        self.assertTrue(callable(getattr(video_upscaler.cli, "main", None)))


if __name__ == "__main__":
    unittest.main()
