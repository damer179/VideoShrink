#!/usr/bin/env python3
"""
Create a test MP4 file for video compression testing
"""

import subprocess
import os
import sys

def create_test_video():
    """Create a test MP4 file using FFmpeg"""
    
    # Find FFmpeg path
    ffmpeg_path = r"C:\Users\rongg\Code\ffmpeg\bin\ffmpeg.exe"
    if not os.path.exists(ffmpeg_path):
        ffmpeg_path = "ffmpeg"  # Try system PATH
    
    # Output filename
    output_file = "test_video.mp4"
    
    # FFmpeg command to create a test video
    # Creates a 30-second video with:
    # - Colorful test pattern
    # - Audio tone
    # - 1920x1080 resolution
    # - 30fps
    cmd = [
        ffmpeg_path,
        "-f", "lavfi",
        "-i", "testsrc2=duration=30:size=1920x1080:rate=30",
        "-f", "lavfi", 
        "-i", "sine=frequency=1000:duration=30",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-y",  # Overwrite output file
        output_file
    ]
    
    try:
        print(f"Creating test video: {output_file}")
        print("This will take about 10-15 seconds...")
        
        # Run FFmpeg command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Get file size
            file_size = os.path.getsize(output_file) / (1024 * 1024)
            print(f"[SUCCESS] Test video created successfully!")
            print(f"File: {output_file}")
            print(f"Size: {file_size:.1f} MB")
            print(f"Duration: 30 seconds")
            print(f"Resolution: 1920x1080")
            print(f"Audio: 1kHz tone")
            print("\nYou can now use this file to test the MP4 compressor!")
        else:
            print(f"[ERROR] Error creating test video:")
            print(result.stderr)
            
    except FileNotFoundError:
        print("[ERROR] FFmpeg not found. Please make sure FFmpeg is installed and in your PATH.")
        print("You can install it from: https://ffmpeg.org/download.html")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    create_test_video()