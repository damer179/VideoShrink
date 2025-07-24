#!/usr/bin/env python3
"""
Test script to check if the web app is working
"""

import requests
import os

def test_upload():
    """Test the upload functionality"""
    
    # Check if test video exists
    test_file = "test_video.mp4"
    if not os.path.exists(test_file):
        print("Error: test_video.mp4 not found. Run create_test_video.py first.")
        return
    
    # Test data
    url = "http://localhost:5000/upload"
    
    files = {
        'video': ('test_video.mp4', open(test_file, 'rb'), 'video/mp4')
    }
    
    data = {
        'output_filename': 'test_compressed.mp4',
        'bitrate': '2M'
    }
    
    try:
        print("Testing file upload...")
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Upload successful! Job ID: {result['job_id']}")
            return result['job_id']
        else:
            print(f"Upload failed: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to server. Make sure the Flask app is running.")
        print("Run: python run_web.py")
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        files['video'][1].close()

if __name__ == "__main__":
    test_upload()