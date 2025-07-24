#!/usr/bin/env python3
"""
Web launcher for MP4 Compressor
Run this file to start the web interface
"""

import os
import sys
import webbrowser
import time
import threading
from app import app

def open_browser():
    """Open browser after a short delay"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("🎬 Starting MP4 Compressor Web Interface...")
    print("📡 Server will be available at: http://localhost:5000")
    print("🌐 Opening browser automatically...")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Open browser in background
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start Flask app
    try:
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Goodbye!")
        sys.exit(0)