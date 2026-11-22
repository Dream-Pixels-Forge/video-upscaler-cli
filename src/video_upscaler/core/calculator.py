"""Resolution calculation, aspect ratio management, and canvas fitting."""

from typing import Optional, Union

from video_upscaler.core.types import (
    FitStrategy,
    LowResolutionError,
    Preset,
    TargetResolution,
)


def _round_even(val: float) -> int:
    """Round a floating-point dimension to the nearest even integer >= 2."""
    rounded = int(round(val / 2.0)) * 2
    return max(2, rounded)


class ResolutionCalculator:
    """Calculates target video resolutions, scaling factors, padding, and cropping."""

    MIN_360P_DIM = 360

    @classmethod
    def calculate_target_resolution(
        cls,
        source_w: int,
        source_h: int,
        preset: Optional[Union[Preset, str]] = None,
        fit_strategy: Union[FitStrategy, str] = FitStrategy.FIT,
        custom_w: Optional[int] = None,
        custom_h: Optional[int] = None,
        scale_factor: Optional[float] = None,
        allow_low_res: bool = False,
        dci: bool = False,
    ) -> TargetResolution:
        """Calculate target resolution, scaled dimensions, padding, or crop offsets.

        Args:
            source_w: Source video width in pixels.
            source_h: Source video height in pixels.
            preset: Standard preset (720p, 1080p, 2k, dci_2k, custom).
            fit_strategy: FitStrategy (FIT, PAD, CROP). Default FIT.
            custom_w: Optional custom canvas/target width.
            custom_h: Optional custom canvas/target height.
            scale_factor: Optional multiplier (e.g. 2.0 for 2x scale).
            allow_low_res: If False, raises LowResolutionError for inputs < 360p.
            dci: If True, uses DCI 2K (2048x1080) for 2K preset.

        Returns:
            TargetResolution containing target dimensions and transformation parameters.
        """
        if source_w <= 0 or source_h <= 0:
            raise ValueError(f"Source dimensions must be positive integers, got {source_w}x{source_h}")

        # Validate minimum 360p input
        min_dim = min(source_w, source_h)
        if min_dim < cls.MIN_360P_DIM and not allow_low_res:
            raise LowResolutionError(
                f"Input resolution {source_w}x{source_h} is below minimum 360p threshold "
                f"({min_dim} < {cls.MIN_360P_DIM}). Use allow_low_res=True to override."
            )

        # Normalize fit strategy
        if isinstance(fit_strategy, str):
            fit_strategy = FitStrategy.from_str(fit_strategy)

        # 1. Direct scale factor case
        if scale_factor is not None:
            scaled_w = _round_even(source_w * scale_factor)
            scaled_h = _round_even(source_h * scale_factor)
            return TargetResolution(
                width=scaled_w,
                height=scaled_h,
                scaled_width=scaled_w,
                scaled_height=scaled_h,
            )

        # Normalize preset
        if isinstance(preset, str):
            preset = Preset.from_str(preset)

        is_vertical = source_h > source_w

        # 2. Determine target canvas dimensions
        if custom_w is not None and custom_h is not None:
            canvas_w = _round_even(custom_w)
            canvas_h = _round_even(custom_h)
        elif custom_w is not None:
            canvas_w = _round_even(custom_w)
            canvas_h = _round_even(custom_w * (source_h / source_w))
        elif custom_h is not None:
            canvas_h = _round_even(custom_h)
            canvas_w = _round_even(custom_h * (source_w / source_h))
        else:
            if preset is None:
                preset = Preset.RES_1080P

            if preset == Preset.RES_720P:
                canvas_w, canvas_h = (720, 1280) if is_vertical else (1280, 720)
            elif preset == Preset.RES_1080P:
                canvas_w, canvas_h = (1080, 1920) if is_vertical else (1920, 1080)
            elif preset == Preset.RES_2K:
                if dci:
                    canvas_w, canvas_h = (1080, 2048) if is_vertical else (2048, 1080)
                else:
                    canvas_w, canvas_h = (1440, 2560) if is_vertical else (2560, 1440)
            elif preset == Preset.RES_DCI_2K:
                canvas_w, canvas_h = (1080, 2048) if is_vertical else (2048, 1080)
            elif preset == Preset.RES_4K:
                if dci:
                    canvas_w, canvas_h = (2160, 4096) if is_vertical else (4096, 2160)
                else:
                    canvas_w, canvas_h = (2160, 3840) if is_vertical else (3840, 2160)
            elif preset == Preset.RES_DCI_4K:
                canvas_w, canvas_h = (2160, 4096) if is_vertical else (4096, 2160)
            elif preset == Preset.RES_8K:
                if dci:
                    canvas_w, canvas_h = (4320, 8192) if is_vertical else (8192, 4320)
                else:
                    canvas_w, canvas_h = (4320, 7680) if is_vertical else (7680, 4320)
            elif preset == Preset.RES_DCI_8K:
                canvas_w, canvas_h = (4320, 8192) if is_vertical else (8192, 4320)
            elif preset == Preset.CUSTOM:
                raise ValueError("Preset.CUSTOM requires explicit custom_w and custom_h or scale_factor")
            else:
                raise ValueError(f"Unsupported preset: {preset}")

        # 3. Apply fit strategy
        if fit_strategy == FitStrategy.FIT:
            # If explicit custom_w and custom_h were specified, use them directly
            if custom_w is not None and custom_h is not None:
                return TargetResolution(
                    width=canvas_w,
                    height=canvas_h,
                    scaled_width=canvas_w,
                    scaled_height=canvas_h,
                )

            # Preserve source aspect ratio anchored to target height (landscape) or width (portrait)
            if is_vertical:
                target_w = canvas_w
                target_h = _round_even(canvas_w * (source_h / source_w))
            else:
                target_h = canvas_h
                target_w = _round_even(canvas_h * (source_w / source_h))

            return TargetResolution(
                width=target_w,
                height=target_h,
                scaled_width=target_w,
                scaled_height=target_h,
            )

        elif fit_strategy == FitStrategy.PAD:
            # Scale video to fit within canvas bounds, pad the remainder
            scale = min(canvas_w / source_w, canvas_h / source_h)
            scaled_w = min(canvas_w, _round_even(source_w * scale))
            scaled_h = min(canvas_h, _round_even(source_h * scale))

            pad_total_x = canvas_w - scaled_w
            pad_total_y = canvas_h - scaled_h

            pad_x = _round_even(pad_total_x / 2.0) if pad_total_x >= 2 else 0
            pad_y = _round_even(pad_total_y / 2.0) if pad_total_y >= 2 else 0

            return TargetResolution(
                width=canvas_w,
                height=canvas_h,
                scaled_width=scaled_w,
                scaled_height=scaled_h,
                pad_x=pad_x,
                pad_y=pad_y,
            )

        elif fit_strategy == FitStrategy.CROP:
            # Scale video to cover canvas bounds, center-crop overflow
            scale = max(canvas_w / source_w, canvas_h / source_h)
            scaled_w = max(canvas_w, _round_even(source_w * scale))
            scaled_h = max(canvas_h, _round_even(source_h * scale))

            crop_total_x = scaled_w - canvas_w
            crop_total_y = scaled_h - canvas_h

            crop_x = _round_even(crop_total_x / 2.0) if crop_total_x >= 2 else 0
            crop_y = _round_even(crop_total_y / 2.0) if crop_total_y >= 2 else 0

            return TargetResolution(
                width=canvas_w,
                height=canvas_h,
                scaled_width=scaled_w,
                scaled_height=scaled_h,
                crop_x=crop_x,
                crop_y=crop_y,
                crop_w=canvas_w,
                crop_h=canvas_h,
            )

        raise ValueError(f"Unknown fit strategy: {fit_strategy}")
