from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.middleware.gzip import GZipMiddleware
import os
import uuid
import threading
from mp4_compressor import compress_mp4_for_youtube
import time

app = Flask(__name__, static_folder='static')
app.wsgi_app = GZipMiddleware(app.wsgi_app)
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
        
        # Initialize status
        compression_status[job_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Starting compression...',
            'input_file': filename,
            'output_file': output_filename
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
        compression_status[job_id]['message'] = 'Compressing video...'
        compression_status[job_id]['progress'] = 10
        
        # Custom compression function that updates status
        compress_with_status(job_id, input_path, output_path, bitrate)
        
        compression_status[job_id]['status'] = 'completed'
        compression_status[job_id]['progress'] = 100
        compression_status[job_id]['message'] = 'Compression completed!'
        compression_status[job_id]['download_path'] = output_path
        
    except Exception as e:
        compression_status[job_id]['status'] = 'error'
        compression_status[job_id]['message'] = f'Error: {str(e)}'

def compress_with_status(job_id, input_path, output_path, bitrate):
    # Simplified version of compression with status updates
    compression_status[job_id]['progress'] = 30
    compression_status[job_id]['message'] = 'Analyzing video...'
    
    # Call the original compression function
    compress_mp4_for_youtube(input_path, output_path, bitrate)
    
    compression_status[job_id]['progress'] = 90
    compression_status[job_id]['message'] = 'Finalizing...'

@app.route('/status/<job_id>')
def get_status(job_id):
    if job_id not in compression_status:
        return jsonify({'error': 'Job not found'}), 404
    
    status = compression_status[job_id].copy()
    
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