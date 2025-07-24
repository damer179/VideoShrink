import requests
import time
import os

def compress_with_cloudconvert(input_file, output_file, api_key, target_bitrate="2M"):
    """
    Compress MP4 using CloudConvert API
    Sign up at: https://cloudconvert.com/api/v2
    """
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Step 1: Create job
    job_data = {
        "tasks": {
            "import-file": {
                "operation": "import/upload"
            },
            "compress-video": {
                "operation": "convert",
                "input": "import-file",
                "output_format": "mp4",
                "options": {
                    "video_codec": "libx264",
                    "video_bitrate": target_bitrate,
                    "audio_codec": "aac",
                    "audio_bitrate": "128k",
                    "preset": "medium",
                    "crf": 23
                }
            },
            "export-file": {
                "operation": "export/url",
                "input": "compress-video"
            }
        }
    }
    
    # Create job
    response = requests.post('https://api.cloudconvert.com/v2/jobs', 
                           headers=headers, json=job_data)
    job = response.json()
    
    if response.status_code != 201:
        raise Exception(f"Failed to create job: {job}")
    
    job_id = job['data']['id']
    upload_task = job['data']['tasks'][0]
    
    # Step 2: Upload file
    upload_url = upload_task['result']['form']['url']
    upload_data = upload_task['result']['form']['parameters']
    
    with open(input_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(upload_url, data=upload_data, files=files)
    
    if response.status_code != 201:
        raise Exception("Failed to upload file")
    
    # Step 3: Wait for completion
    while True:
        response = requests.get(f'https://api.cloudconvert.com/v2/jobs/{job_id}', 
                              headers=headers)
        job_status = response.json()
        
        if job_status['data']['status'] == 'finished':
            break
        elif job_status['data']['status'] == 'error':
            raise Exception("Compression failed")
        
        time.sleep(2)
    
    # Step 4: Download result
    export_task = [task for task in job_status['data']['tasks'] 
                   if task['name'] == 'export-file'][0]
    download_url = export_task['result']['files'][0]['url']
    
    response = requests.get(download_url)
    with open(output_file, 'wb') as f:
        f.write(response.content)
    
    return True

def compress_with_api2convert(input_file, output_file, api_key, target_bitrate="2M"):
    """
    Compress MP4 using API2Convert
    Sign up at: https://www.api2convert.com/
    """
    
    url = "https://api.api2convert.com/v2/jobs"
    
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    
    # Upload and convert in one request
    with open(input_file, 'rb') as f:
        files = {
            'file': f
        }
        data = {
            'output_format': 'mp4',
            'video_bitrate': target_bitrate,
            'audio_bitrate': '128k',
            'video_codec': 'h264',
            'audio_codec': 'aac'
        }
        
        response = requests.post(url, headers=headers, files=files, data=data)
    
    if response.status_code != 200:
        raise Exception(f"API request failed: {response.text}")
    
    result = response.json()
    job_id = result['job_id']
    
    # Poll for completion
    while True:
        status_response = requests.get(f"{url}/{job_id}", headers=headers)
        status = status_response.json()
        
        if status['status'] == 'completed':
            # Download result
            download_response = requests.get(status['download_url'])
            with open(output_file, 'wb') as f:
                f.write(download_response.content)
            return True
        elif status['status'] == 'failed':
            raise Exception("Compression failed")
        
        time.sleep(3)

def compress_with_bannerbear(input_file, output_file, api_key, target_bitrate="2M"):
    """
    Compress MP4 using Bannerbear API
    Sign up at: https://www.bannerbear.com/
    """
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Upload file first
    with open(input_file, 'rb') as f:
        files = {'file': f}
        upload_response = requests.post(
            'https://api.bannerbear.com/v2/videos/upload',
            headers={'Authorization': f'Bearer {api_key}'},
            files=files
        )
    
    if upload_response.status_code != 200:
        raise Exception("Upload failed")
    
    video_url = upload_response.json()['video_url']
    
    # Create compression job
    job_data = {
        'input_media_url': video_url,
        'output_format': 'mp4',
        'video_settings': {
            'codec': 'h264',
            'bitrate': target_bitrate,
            'preset': 'medium'
        },
        'audio_settings': {
            'codec': 'aac',
            'bitrate': '128k'
        }
    }
    
    response = requests.post('https://api.bannerbear.com/v2/videos/compress',
                           headers=headers, json=job_data)
    
    if response.status_code != 200:
        raise Exception("Compression job failed")
    
    job = response.json()
    job_id = job['uid']
    
    # Wait for completion
    while True:
        status_response = requests.get(
            f'https://api.bannerbear.com/v2/videos/{job_id}',
            headers=headers
        )
        status = status_response.json()
        
        if status['status'] == 'completed':
            # Download result
            download_response = requests.get(status['video_url'])
            with open(output_file, 'wb') as f:
                f.write(download_response.content)
            return True
        elif status['status'] == 'failed':
            raise Exception("Compression failed")
        
        time.sleep(5)

# Main compression function that tries different APIs
def compress_mp4_for_youtube_api(input_file, output_file, target_bitrate="2M"):
    """
    Compress MP4 using cloud APIs as fallback options
    """
    
    # Try CloudConvert (most reliable)
    cloudconvert_key = os.getenv('CLOUDCONVERT_API_KEY')
    if cloudconvert_key:
        try:
            return compress_with_cloudconvert(input_file, output_file, 
                                            cloudconvert_key, target_bitrate)
        except Exception as e:
            print(f"CloudConvert failed: {e}")
    
    # Try API2Convert
    api2convert_key = os.getenv('API2CONVERT_API_KEY')
    if api2convert_key:
        try:
            return compress_with_api2convert(input_file, output_file, 
                                           api2convert_key, target_bitrate)
        except Exception as e:
            print(f"API2Convert failed: {e}")
    
    # Try Bannerbear
    bannerbear_key = os.getenv('BANNERBEAR_API_KEY')
    if bannerbear_key:
        try:
            return compress_with_bannerbear(input_file, output_file, 
                                          bannerbear_key, target_bitrate)
        except Exception as e:
            print(f"Bannerbear failed: {e}")
    
    raise Exception("No API keys configured or all APIs failed")