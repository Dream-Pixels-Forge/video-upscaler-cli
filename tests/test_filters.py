"""Tests for the precision filter chain builder (TASK-3)."""

import pytest

from video_upscaler.filters import build_filter_chain
from video_upscaler.filters.chain import build_filter_chain as build_filter_chain_direct

SCALE = "scale={w}:{h}:flags=lanczos+accurate_rnd+full_chroma_int+full_chroma_inp"
SHARPEN = "unsharp=lx=5:ly=5:la=0.6:cx=3:cy=3:ca=0.3"
DEBAND = "deband=1:64:16:16"


class TestImportContract:
    def test_reexported_from_package(self) -> None:
        assert callable(build_filter_chain)

    def test_importable_from_chain_module(self) -> None:
        assert callable(build_filter_chain_direct)


class TestDefaultChain:
    def test_default_is_gentle_denoise_scale_sharpen(self) -> None:
        chain = build_filter_chain(1280, 720)
        assert chain == f"hqdn3d=1.5:1.5:3:3,{SCALE.format(w=1280, h=720)},{SHARPEN}"

    def test_returns_single_string(self) -> None:
        assert isinstance(build_filter_chain(1280, 720), str)

    def test_no_trailing_comma(self) -> None:
        chain = build_filter_chain(1280, 720)
        assert not chain.endswith(",")
        assert not chain.startswith(",")

    def test_scale_filter_always_present(self) -> None:
        chain = build_filter_chain(1920, 1080, denoise="none", sharpen=False)
        assert SCALE.format(w=1920, h=1080) in chain


class TestDenoiseLevels:
    def test_none_adds_no_denoise_filter(self) -> None:
        chain = build_filter_chain(1280, 720, denoise="none", sharpen=False)
        assert chain == SCALE.format(w=1280, h=720)

    def test_gentle(self) -> None:
        chain = build_filter_chain(1280, 720, denoise="gentle", sharpen=False)
        assert chain == f"hqdn3d=1.5:1.5:3:3,{SCALE.format(w=1280, h=720)}"

    def test_medium(self) -> None:
        chain = build_filter_chain(1280, 720, denoise="medium", sharpen=False)
        assert chain == f"hqdn3d=3:3:6:6,{SCALE.format(w=1280, h=720)}"

    def test_strong(self) -> None:
        chain = build_filter_chain(1280, 720, denoise="strong", sharpen=False)
        assert chain == f"atadenoise,{SCALE.format(w=1280, h=720)}"


class TestOptionalStages:
    def test_sharpen_disabled(self) -> None:
        chain = build_filter_chain(1280, 720, sharpen=False)
        assert "unsharp" not in chain
        assert chain.endswith(SCALE.format(w=1280, h=720))

    def test_deband_enabled(self) -> None:
        chain = build_filter_chain(1280, 720, deband=True)
        assert chain.endswith(f",{DEBAND}")
        assert DEBAND in chain

    def test_deband_disabled_by_default(self) -> None:
        chain = build_filter_chain(1280, 720)
        assert "deband" not in chain


class TestFullPipeline:
    def test_all_options_combined(self) -> None:
        chain = build_filter_chain(1920, 1080, denoise="strong", sharpen=True, deband=True)
        assert chain == (
            f"atadenoise,{SCALE.format(w=1920, h=1080)},{SHARPEN},{DEBAND}"
        )

    def test_stage_order_denoise_scale_sharpen_deband(self) -> None:
        chain = build_filter_chain(2560, 1440, denoise="medium", sharpen=True, deband=True)
        i_denoise = chain.index("hqdn3d")
        i_scale = chain.index("scale=")
        i_sharpen = chain.index("unsharp")
        i_deband = chain.index("deband")
        assert i_denoise < i_scale < i_sharpen < i_deband


class TestValidation:
    @pytest.mark.parametrize("w, h", [(1280, 719), (1281, 720), (641, 361)])
    def test_odd_dimensions_raise(self, w: int, h: int) -> None:
        with pytest.raises(ValueError):
            build_filter_chain(w, h)

    @pytest.mark.parametrize("w, h", [(0, 720), (1280, 0), (-1, 720), (1280, -720)])
    def test_non_positive_dimensions_raise(self, w: int, h: int) -> None:
        with pytest.raises(ValueError):
            build_filter_chain(w, h)

    def test_unknown_denoise_raises(self) -> None:
        with pytest.raises(ValueError):
            build_filter_chain(1280, 720, denoise="aggressive")

    def test_non_integer_dimensions_raise(self) -> None:
        with pytest.raises(ValueError):
            build_filter_chain(1280.5, 720)
