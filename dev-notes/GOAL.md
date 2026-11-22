# GOAL: Video Upscaler Tool

## Target State
Deliver a robust, tested, and reliable video upscaler CLI and library (`video-upscaler-cli`) capable of upscaling video from minimum 360p up to 720p, 1080p, and 2K (2560x1440 / 2048x1080) with high accuracy, detail preservation, artifact mitigation, and strict temporal consistency.

## Deliverables
1. Python package `video_upscaler` with clean modular architecture:
   - `core/`: Config, Presets, Probe, VideoInfo, Resolution calculations.
   - `engines/`: BaseEngine, FFmpegPrecisionEngine, RealESRGANEngine (adapter/fallback).
   - `filters/`: Filter graph builders for multi-stage precision upscaling (Lanczos, CAS, unsharp, deband, denoise, color matrix).
   - `cli/`: Command-line interface with preset resolution flags (`--preset 2k|1080p|720p`), progress tracking, and batch processing.
2. CLI binary: `video-upscale` / `python -m video_upscaler`.
3. Complete test suite (`tests/`):
   - Unit tests for probe, dimension calculators, filter builders, validation.
   - Integration tests with synthetic test videos generated via ffmpeg testsrc (e.g. 640x360 -> 720p, 1080p, 2K).
   - Audio/stream preservation tests.
4. Comprehensive documentation in `README.md`.

## Verification Gates
- [ ] Gate 1: Code style & linting clean (no syntax errors, standard formatting).
- [ ] Gate 2: Unit tests pass (`pytest tests/ -v`).
- [ ] Gate 3: Integration tests pass with real video upscaling (360p -> 720p, 1080p, 2K).
- [ ] Gate 4: Aspect ratio & dimension invariants strictly verified (divisible by 2, correct pixel dimensions).
- [ ] Gate 5: CLI execution verified (`video-upscale --help` and actual run).
