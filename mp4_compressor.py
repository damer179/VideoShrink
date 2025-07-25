import ffmpeg
import os
import sys
import shutil
import threading
import time
from tqdm import tqdm

def find_ffmpeg():
    """Find FFmpeg executable path"""
    # Check Heroku buildpack path first (production)
    heroku_ffmpeg = "/app/vendor/ffmpeg/ffmpeg"
    if os.path.exists(heroku_ffmpeg):
        return heroku_ffmpeg
    
    # Then try system PATH
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    
    # Check for ffmpeg using relative paths (local development)
    local_paths = [
        "ffmpeg.exe",
        "ffmpeg/ffmpeg.exe",
        "ffmpeg/bin/ffmpeg.exe"
    ]
    
    # Try relative paths last
    for path in local_paths:
        if os.path.exists(path):
            return path
    
    return None

def monitor_output_file(output_file, original_size, stop_event):
    """Monitor output file size during compression"""
    while not os.path.exists(output_file) and not stop_event.is_set():
        time.sleep(0.5)
    
    while not stop_event.is_set():
        try:
            if os.path.exists(output_file):
                current_size = os.path.getsize(output_file) / (1024 * 1024)
                compression_ratio = (1 - current_size / original_size) * 100
                print(f"\rCurrent: {current_size:.1f}MB | Reduction: {compression_ratio:.1f}%", end="", flush=True)
            time.sleep(1)
        except:
            break

def print_compression_summary(input_file, output_file, video_info, bitrate, crf, processing_time):
    """Print detailed compression summary with visual elements"""
    original_size = os.path.getsize(input_file) / (1024 * 1024)
    compressed_size = os.path.getsize(output_file) / (1024 * 1024)
    compression_ratio = (1 - compressed_size / original_size) * 100
    
    # Format processing time
    minutes = int(processing_time // 60)
    seconds = int(processing_time % 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    print("\n" + "="*50)
    print("           COMPRESSION COMPLETE")
    print("="*50)
    print(f"📁 Input:  {input_file}")
    print(f"📁 Output: {output_file}")
    print(f"📐 Resolution: {video_info['width']}x{video_info['height']}")
    print(f"⚙️  Settings: Bitrate={bitrate}, CRF={crf}")
    print("-"*50)
    print(f"📊 Original:   {original_size:>8.2f} MB")
    print(f"📊 Compressed: {compressed_size:>8.2f} MB")
    print(f"📈 Reduction:  {compression_ratio:>8.1f}%")
    print(f"⏱️  Time:      {time_str:>8s}")
    
    # Visual bar
    bar_length = 30
    filled = int(compression_ratio * bar_length / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"📊 Progress:   [{bar}] {compression_ratio:.1f}%")
    print("="*50)

def compress_mp4_for_youtube(input_file, output_file, target_bitrate="2M"):
    """
    Compress MP4 file for YouTube upload while preserving audio quality.
    
    Args:
        input_file: Path to input MP4 file
        output_file: Path to output compressed MP4 file
        target_bitrate: Video bitrate (default: 2M for 1080p)
    """
    start_time = time.time()
    
    try:
        # Find FFmpeg executable
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            raise Exception("FFmpeg not found. Please install FFmpeg and add to PATH or place in C:\\ffmpeg\\bin\\")
        
        # Check if input file exists
        if not os.path.exists(input_file):
            raise Exception(f"Input file '{input_file}' not found")
        
        # Get input file info
        try:
            if ffmpeg_path != "ffmpeg":
                # Use custom ffprobe path
                if ffmpeg_path.endswith('.exe'):
                    ffprobe_path = ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
                else:
                    ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
                probe = ffmpeg.probe(input_file, cmd=ffprobe_path)
            else:
                probe = ffmpeg.probe(input_file)
        except ffmpeg.Error as e:
            raise Exception(f"Invalid video file '{input_file}': {e.stderr.decode() if e.stderr else 'Unknown error'}")
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        width = int(video_info['width'])
        height = int(video_info['height'])
        
        # Determine optimal settings based on resolution
        if height >= 1080:
            bitrate = target_bitrate
            crf = 23
        elif height >= 720:
            bitrate = "1.5M"
            crf = 24
        else:
            bitrate = "1M"
            crf = 25
        
        # Display compression info
        print(f"\nCompressing {input_file}...")
        print(f"Settings: {width}x{height}, Bitrate: {bitrate}, CRF: {crf}")
        
        # Start file size monitoring
        original_size_mb = os.path.getsize(input_file) / (1024 * 1024)
        stop_event = threading.Event()
        monitor_thread = threading.Thread(target=monitor_output_file, 
                                        args=(output_file, original_size_mb, stop_event))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Compress video
        input_stream = ffmpeg.input(input_file)
        
        # Process video and audio streams separately then combine
        video_stream = input_stream['v:0'].filter('scale', width, height)
        audio_stream = input_stream['a:0']
        
        # Output with both video and audio
        output = ffmpeg.output(
            video_stream, audio_stream,
            output_file,
            vcodec='libx264',
            preset='medium',  # Balance between speed and compression
            crf=crf,          # Constant Rate Factor for quality
            maxrate=bitrate,  # Maximum bitrate
            bufsize=f"{int(bitrate[:-1]) * 2}M",  # Buffer size
            pix_fmt='yuv420p',  # YouTube compatible pixel format
            acodec='aac',     # High quality audio codec
            audio_bitrate='128k',  # Good audio quality without bloat
            ac=2,             # Stereo audio
            ar=44100,         # Standard sample rate
            movflags='faststart'  # Optimize for web streaming
        )
        
        # Create progress bar
        print("\nCompressing...")
        pbar = tqdm(total=100, desc="Progress", unit="%", ncols=70)
        
        try:
            if ffmpeg_path != "ffmpeg":
                ffmpeg.run(output, overwrite_output=True, quiet=True, cmd=ffmpeg_path)
            else:
                ffmpeg.run(output, overwrite_output=True, quiet=True)
            pbar.update(100)
        finally:
            pbar.close()
            stop_event.set()
            monitor_thread.join(timeout=1)
        
        # Calculate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Show visual compression summary
        print_compression_summary(input_file, output_file, video_info, bitrate, crf, processing_time)
        
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e.stderr.decode() if e.stderr else 'Unknown FFmpeg error'}")
    except Exception as e:
        print(f"Error compressing video: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python mp4_compressor.py input_file.mp4 output_file.mp4")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"Input file '{input_file}' not found")
        sys.exit(1)
    
    compress_mp4_for_youtube(input_file, output_file)