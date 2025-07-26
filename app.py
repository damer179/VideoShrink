from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import uuid
import threading
from mp4_compressor import compress_mp4_for_youtube
import time

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for large files

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Store compression status
compression_status = {}

def cleanup_old_files():
    """Remove files older than 1 hour"""
    import glob
    current_time = time.time()
    
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
        for file_path in glob.glob(os.path.join(folder, '*')):
            try:
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > 3600:  # 1 hour
                        os.remove(file_path)
                        print(f"Cleaned up old file: {file_path}")
            except Exception as e:
                print(f"Error cleaning up {file_path}: {e}")

# Run cleanup every hour
import threading
def periodic_cleanup():
    cleanup_old_files()
    threading.Timer(3600, periodic_cleanup).start()  # Run every hour

periodic_cleanup()  # Start cleanup timer

@app.route('/')
def index():
    response = app.make_response(render_template('index.html'))
    response.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes
    return response

@app.route('/debug')
def debug():
    from mp4_compressor import find_ffmpeg
    ffmpeg_path = find_ffmpeg()
    return f"FFmpeg path: {ffmpeg_path}"
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        print(f"Upload request received. Files: {list(request.files.keys())}")
        print(f"Form data: {dict(request.form)}")
        
        if 'video' not in request.files:
            return jsonify({'error': 'No video file uploaded'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.mp4'):
            return jsonify({'error': 'Only MP4 files are supported'}), 400
        
        print(f"Processing file: {file.filename}")
        
        # Generate unique ID for this compression job
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
        file.save(input_path)
        
        # Get parameters
        output_filename = request.form.get('output_filename', 'compressed_video.mp4')
        if not output_filename.endswith('.mp4'):
            output_filename += '.mp4'
        
        bitrate = request.form.get('bitrate', '2M')
        
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_{output_filename}")
        
        # Get file size for initial info
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        
        # Initialize status
        compression_status[job_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Initializing...',
            'input_file': filename,
            'output_file': output_filename,
            'file_size': f'{file_size_mb:.1f} MB',
            'start_time': time.time()
        }
        
        # Start compression in background
        thread = threading.Thread(target=compress_video_background, 
                                args=(job_id, input_path, output_path, bitrate))
        thread.daemon = True
        thread.start()
        
        print(f"Job created: {job_id}")
        return jsonify({'job_id': job_id})
        
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

def compress_video_background(job_id, input_path, output_path, bitrate):
    try:
        compression_status[job_id]['message'] = 'Preparing video...'
        compression_status[job_id]['progress'] = 8
        
        # Get video info first
        import ffmpeg
        from mp4_compressor import find_ffmpeg
        
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            raise Exception("FFmpeg not found")
        
        # Fast estimation - skip slow video probing
        try:
            file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
            estimated_duration = file_size_mb / 2  # Rough estimate: 2MB per second
            
            compression_status[job_id]['duration'] = estimated_duration
            compression_status[job_id]['video_info'] = {
                'width': 1920, 'height': 1080, 'fps': 30  # Use defaults
            }
        except:
            compression_status[job_id]['duration'] = 0
            compression_status[job_id]['video_info'] = {'width': 1920, 'height': 1080, 'fps': 30}
        
        compression_status[job_id]['progress'] = 15
        compression_status[job_id]['message'] = 'Starting compression...'
        
        # Start compression with real-time progress
        compress_with_realtime_progress(job_id, input_path, output_path, bitrate)
        
        print(f"Compression completed for job {job_id}")
        compression_status[job_id]['status'] = 'completed'
        compression_status[job_id]['progress'] = 100
        compression_status[job_id]['message'] = 'Compression completed!'
        compression_status[job_id]['download_path'] = output_path
        print(f"Job {job_id} marked as completed, file at: {output_path}")
        
    except Exception as e:
        print(f"Compression error for job {job_id}: {str(e)}")
        compression_status[job_id]['status'] = 'error'
        compression_status[job_id]['message'] = f'Error: {str(e)}'
        
        # Cleanup files on error
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception as cleanup_error:
            print(f"Cleanup error for failed job {job_id}: {cleanup_error}")

def compress_with_realtime_progress(job_id, input_path, output_path, bitrate):
    import subprocess
    import re
    from mp4_compressor import find_ffmpeg
    
    ffmpeg_path = find_ffmpeg()
    duration = compression_status[job_id].get('duration', 0)
    
    # Optimized FFmpeg command for faster processing
    cmd = [
        ffmpeg_path,
        '-i', input_path,
        '-c:v', 'libx264',
        '-preset', 'veryfast',  # Even faster preset
        '-crf', '23',
        '-maxrate', bitrate,
        '-bufsize', f"{int(bitrate[:-1]) * 2}M",
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ac', '2',
        '-ar', '44100',
        '-movflags', 'faststart',
        '-threads', '0',  # Use all available CPU cores
        '-progress', 'pipe:1',  # Output progress to stdout
        '-y',  # Overwrite output file
        output_path
    ]
    
    compression_status[job_id]['message'] = 'Encoding video...'
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              universal_newlines=True, bufsize=1)
    
    current_time = 0
    for line in process.stdout:
        try:
            if line.startswith('out_time_ms='):
                time_str = line.split('=')[1].strip()
                if time_str and time_str != 'N/A':
                    time_ms = int(time_str)
                    current_time = time_ms / 1000000  # Convert to seconds
                    
                    if duration > 0:
                        progress = min(int((current_time / duration) * 80) + 10, 95)  # 10-95%
                        compression_status[job_id]['progress'] = progress
                        compression_status[job_id]['message'] = f'Encoding... {current_time:.1f}s / {duration:.1f}s'
            
            elif line.startswith('speed='):
                speed = line.split('=')[1].strip()
                if 'x' in speed and speed != 'N/A':
                    compression_status[job_id]['speed'] = speed
        except (ValueError, IndexError):
            continue  # Skip invalid lines
    
    process.wait()
    
    if process.returncode != 0:
        try:
            error = process.stderr.read()
        except:
            error = "Unknown FFmpeg error"
        raise Exception(f"FFmpeg error: {error}")
    
    compression_status[job_id]['progress'] = 95
    compression_status[job_id]['message'] = 'Finalizing...'

@app.route('/status/<job_id>')
def get_status(job_id):
    if job_id not in compression_status:
        return jsonify({'error': 'Job not found'}), 404
    
    status = compression_status[job_id].copy()
    
    # Add elapsed time
    if 'start_time' in status:
        elapsed = time.time() - status['start_time']
        status['elapsed_time'] = f'{int(elapsed//60)}m {int(elapsed%60)}s' if elapsed >= 60 else f'{int(elapsed)}s'
    
    # Add estimated time remaining
    if status.get('progress', 0) > 10 and 'start_time' in status:
        elapsed = time.time() - status['start_time']
        progress_ratio = status['progress'] / 100
        if progress_ratio > 0:
            total_estimated = elapsed / progress_ratio
            remaining = max(0, total_estimated - elapsed)
            status['eta'] = f'{int(remaining//60)}m {int(remaining%60)}s' if remaining >= 60 else f'{int(remaining)}s'
    
    # Add current output file size during processing
    if status['status'] == 'processing' and 'download_path' in compression_status[job_id]:
        output_path = compression_status[job_id]['download_path']
        if os.path.exists(output_path):
            current_size = os.path.getsize(output_path) / (1024 * 1024)
            status['current_size'] = f'{current_size:.1f} MB'
    
    # Add file size info if completed
    if status['status'] == 'completed' and 'download_path' in status:
        try:
            # Find original file path
            original_path = status['download_path'].replace('outputs', 'uploads')
            original_path = original_path.replace(status['output_file'], status['input_file'])
            
            if os.path.exists(original_path) and os.path.exists(status['download_path']):
                original_size = os.path.getsize(original_path)
                compressed_size = os.path.getsize(status['download_path'])
                status['original_size'] = f"{original_size / (1024*1024):.1f} MB"
                status['compressed_size'] = f"{compressed_size / (1024*1024):.1f} MB"
                status['reduction'] = f"{(1 - compressed_size/original_size) * 100:.1f}%"
        except Exception as e:
            print(f"Error calculating file sizes: {e}")
    
    return jsonify(status)

@app.route('/download/<job_id>')
def download_file(job_id):
    print(f"Download request for job_id: {job_id}")
    
    if job_id not in compression_status:
        print(f"Job {job_id} not found in compression_status")
        return jsonify({'error': 'Job not found'}), 404
    
    job_status = compression_status[job_id]['status']
    print(f"Job {job_id} status: {job_status}")
    
    if job_status != 'completed':
        print(f"Job {job_id} not completed, current status: {job_status}")
        return jsonify({'error': f'File not ready - Status: {job_status}'}), 404
    
    file_path = compression_status[job_id]['download_path']
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Get input file path for cleanup
    input_file = compression_status[job_id]['input_file']
    input_path = file_path.replace('outputs', 'uploads').replace(compression_status[job_id]['output_file'], input_file)
    
    try:
        # Send file to user
        response = send_file(file_path, as_attachment=True, 
                           download_name=compression_status[job_id]['output_file'])
        
        # Schedule cleanup after response is sent
        @response.call_on_close
        def cleanup_files():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(input_path):
                    os.remove(input_path)
                # Remove job from status tracking
                if job_id in compression_status:
                    del compression_status[job_id]
            except Exception as e:
                print(f"Cleanup error for job {job_id}: {e}")
        
        return response
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)