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
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Store compression status
compression_status = {}

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
        compression_status[job_id]['progress'] = 5
        
        # Get video info first
        import ffmpeg
        from mp4_compressor import find_ffmpeg
        
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            raise Exception("FFmpeg not found")
        
        # Get video duration for progress calculation
        try:
            probe = ffmpeg.probe(input_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            duration = float(probe['format']['duration'])
            compression_status[job_id]['duration'] = duration
            compression_status[job_id]['video_info'] = {
                'width': video_info['width'],
                'height': video_info['height'],
                'fps': eval(video_info.get('r_frame_rate', '30/1'))
            }
        except Exception as e:
            duration = 0
        
        compression_status[job_id]['progress'] = 10
        compression_status[job_id]['message'] = f'Starting compression... ({duration:.1f}s video)'
        
        # Start compression with real-time progress
        compress_with_realtime_progress(job_id, input_path, output_path, bitrate)
        
        compression_status[job_id]['status'] = 'completed'
        compression_status[job_id]['progress'] = 100
        compression_status[job_id]['message'] = 'Compression completed!'
        compression_status[job_id]['download_path'] = output_path
        
    except Exception as e:
        compression_status[job_id]['status'] = 'error'
        compression_status[job_id]['message'] = f'Error: {str(e)}'

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
        '-preset', 'fast',  # Faster preset
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
        if line.startswith('out_time_ms='):
            time_ms = int(line.split('=')[1])
            current_time = time_ms / 1000000  # Convert to seconds
            
            if duration > 0:
                progress = min(int((current_time / duration) * 80) + 10, 95)  # 10-95%
                compression_status[job_id]['progress'] = progress
                compression_status[job_id]['message'] = f'Encoding... {current_time:.1f}s / {duration:.1f}s'
        
        elif line.startswith('speed='):
            speed = line.split('=')[1].strip()
            if 'x' in speed:
                compression_status[job_id]['speed'] = speed
    
    process.wait()
    
    if process.returncode != 0:
        error = process.stderr.read()
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
    if job_id not in compression_status or compression_status[job_id]['status'] != 'completed':
        return jsonify({'error': 'File not ready'}), 404
    
    file_path = compression_status[job_id]['download_path']
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=True, 
                    download_name=compression_status[job_id]['output_file'])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)