# Security Requirements: Video Upscaler

## 1. Input Sanitization & Subprocess Security
- **Command Injection Prevention**: FFmpeg and FFprobe must always be called using `subprocess.run` / `subprocess.Popen` with argument lists (argv arrays), NEVER with `shell=True`.
- **Filename & Path Traversal**: Input and output paths must be resolved and validated using `pathlib.Path`.
- **Validation**: Verify file existence and validate media headers using `ffprobe` JSON output before attempting to run processing pipelines.

## 2. Resource Management & Denial of Service Protection
- **Timeout Management**: Long-running upscaling processes support cancellation and timeouts.
- **Disk Space Pre-check**: Avoid filling disk during massive 2K frame renders or temporary file storage.
- **Process Cleanup**: Ensure ffmpeg sub-processes terminate cleanly on SIGINT/SIGTERM or Python exception handling.

## 3. Dependency Security
- Zero unnecessary heavy third-party dependencies for core operation (standard library + optional rich/tqdm).
- Pinned and auditable dependencies.
