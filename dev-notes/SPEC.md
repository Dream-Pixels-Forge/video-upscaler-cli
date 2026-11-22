# Specification: Video Upscaler

## 1. Supported Presets and Resolutions
- **Minimum Input**: 360p (e.g. 640x360 or any resolution where min(width, height) >= 360 or width >= 480).
  - If input is < 360p, tool raises an informative error or warning (with `--allow-low-res` override).
- **Target Presets**:
  - `720p`: Target height 720 (standard 1280x720 for 16:9, or calculated width preserving aspect ratio, even integers).
  - `1080p`: Target height 1080 (standard 1920x1080 for 16:9, or calculated width preserving aspect ratio, even integers).
  - `2k`: Target height 1440 (QHD 2560x1440 for 16:9, or DCI 2K 2048x1080 if specified with `--dci`, or target height 1440 preserving AR).
  - `4k`: Target height 2160 (UHD 3840x2160 for 16:9, or DCI 4K 4096x2160 if specified with `--dci`).
  - `8k`: Target height 4320 (UHD 7680x4320 for 16:9, or DCI 8K 8192x4320 if specified with `--dci`).
  - `custom`: Explicit `--scale 2x`, or explicit `--width W --height H`.

## 2. Fit and Canvas Strategies
- `fit` (default): Calculate target dimensions maintaining source aspect ratio exactly, ensuring both width and height are even numbers (required by H.264/H.265 4:2:0 chroma subsampling).
- `pad`: Scale video to fit within target bounding box and pad with black borders (letterbox/pillarbox) to exact specified canvas dimensions.
- `crop`: Scale video to fill canvas and center-crop overflow.

## 3. High-Accuracy Precision Filtering Pipeline
```
[Input Video]
     │
     ▼
[ffprobe Inspection: resolution, aspect ratio, color space, fps, duration, audio]
     │
     ▼
[Filter Graph Assembly]:
  1. Denoise (Optional, default 'gentle'):
     - 'hqdn3d=1.5:1.5:3:3' or 'atadenoise' to remove 360p compression noise before scaling.
  2. Precision Scaler:
     - 'scale=w:h:flags=lanczos+accurate_rnd+full_chroma_int+full_chroma_inp'
  3. Detail & Edge Restoration:
     - 'unsharp=lx=5:ly=5:la=0.6:cx=3:cy=3:ca=0.3' or adaptive sharpening
  4. Debanding:
     - 'deband=1:64:16:16' to prevent gradient banding when upscaled to 1080p/2K.
  5. 10-bit color intermediate / output encoding:
     - pixel format 'yuv420p' or 'yuv420p10le' for high dynamic range fidelity.
     │
     ▼
[Encoder]:
  - Codec: libx264 (default), libx265 (hevc), prores, or vp9
  - Preset: slow / medium
  - Audio: copy stream (-c:a copy) or fallback to aac
     │
     ▼
[Output Video (720p / 1080p / 2K)]
```

## 4. API & CLI Interface

### CLI:
```bash
video-upscale input.mp4 -p 2k -o output_2k.mp4
video-upscale input.mp4 -p 1080p -o output_1080p.mp4
video-upscale input.mp4 -p 720p -o output_720p.mp4
video-upscale input.mp4 --scale 2 -o output_2x.mp4
video-upscale input.mp4 -p 2k --quality high --denoise gentle --deband
```

### Python API:
```python
from video_upscaler import Upscaler, UpscaleConfig, Preset

config = UpscaleConfig(preset=Preset.RES_2K, quality="high", denoise="gentle")
upscaler = Upscaler(config)
result = upscaler.upscale("input.mp4", "output_2k.mp4")
print(result.output_path, result.resolution, result.duration)
```
