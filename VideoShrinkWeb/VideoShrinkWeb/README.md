# MP4 Compressor for YouTube

A Python script that compresses MP4 files for YouTube upload while maintaining high audio quality and optimal video compression. Features real-time progress monitoring and visual feedback.

## Installation

1. Install Python 3.6 or higher
2. Install FFmpeg on your system:
   - **Windows**: Download from https://ffmpeg.org/download.html
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg`
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Basic Usage

```bash
python mp4_compressor.py input_file.mp4 output_file.mp4
```

## Examples

### Example 1: Basic Compression
```bash
python mp4_compressor.py vacation_video.mp4 vacation_compressed.mp4
```
Output:
```
Compressing vacation_video.mp4...
Settings: 1920x1080, Bitrate: 2M, CRF: 23

Compressing...
Progress: 100%|████████████████████| 100/100 [00:45<00:00,  2.22%/s]
Current: 89.3MB | Reduction: 64.3%

==================================================
           COMPRESSION COMPLETE
==================================================
📁 Input:  vacation_video.mp4
📁 Output: vacation_compressed.mp4
📐 Resolution: 1920x1080
⚙️  Settings: Bitrate=2M, CRF=23
--------------------------------------------------
📊 Original:     250.45 MB
📊 Compressed:    89.32 MB
📈 Reduction:     64.3%
📊 Progress:   [███████████████████░░░░░░░░░░░] 64.3%
==================================================
```

### Example 2: Multiple Files
```bash
# Compress multiple videos
python mp4_compressor.py raw_footage_1.mp4 youtube_ready_1.mp4
python mp4_compressor.py raw_footage_2.mp4 youtube_ready_2.mp4
python mp4_compressor.py raw_footage_3.mp4 youtube_ready_3.mp4
```

### Example 3: Custom Bitrate
Modify the script to use custom bitrate:
```python
compress_mp4_for_youtube("input.mp4", "output.mp4", target_bitrate="1.5M")
```

### Example 4: Batch Processing Script
```python
import os
from mp4_compressor import compress_mp4_for_youtube

input_folder = "raw_videos"
output_folder = "compressed_videos"

for filename in os.listdir(input_folder):
    if filename.endswith(".mp4"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, f"compressed_{filename}")
        compress_mp4_for_youtube(input_path, output_path)
```

## Compression Settings by Resolution

| Resolution | Bitrate | CRF | Typical Size Reduction |
|------------|---------|-----|----------------------|
| 1080p+     | 2M      | 23  | 50-70%              |
| 720p       | 1.5M    | 24  | 45-65%              |
| 480p       | 1M      | 25  | 40-60%              |

## Features

- **Real-time Progress**: Visual progress bar during compression
- **Live Monitoring**: Shows current file size and reduction percentage
- **Visual Summary**: Detailed compression results with emojis and charts
- **Auto-Detection**: Automatically adjusts settings based on video resolution
- **Error Handling**: Clear error messages and troubleshooting guidance

## Audio Quality Settings

- **Codec**: AAC (YouTube preferred)
- **Bitrate**: 128k (high quality)
- **Sample Rate**: 44.1kHz
- **Channels**: Stereo

## Troubleshooting

**Error: FFmpeg not found**
```
Solution: Install FFmpeg and add to system PATH
```

**Error: Input file not found**
```bash
# Check file path
python mp4_compressor.py "C:\Videos\my video.mp4" output.mp4
```

**Large file still too big**
```python
# Use lower bitrate
compress_mp4_for_youtube("input.mp4", "output.mp4", target_bitrate="1M")
```

## File Size Examples

| Original | Compressed | Reduction |
|----------|------------|-----------|
| 500 MB   | 175 MB     | 65%       |
| 1.2 GB   | 420 MB     | 65%       |
| 250 MB   | 95 MB      | 62%       |

## YouTube Upload Guidelines

The compressed files will meet YouTube's requirements:
- ✅ H.264 video codec
- ✅ AAC audio codec
- ✅ MP4 container
- ✅ yuv420p pixel format
- ✅ Optimized for streaming