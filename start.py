#!/usr/bin/env python3
"""
YouTube Video Downloader Startup Script
"""

import os
import sys
import uvicorn
from pathlib import Path

def main():
    """Main startup function"""
    print("🎥 Starting YouTube Video Downloader...")
    print("=" * 50)
    
    # Check if required directories exist
    required_dirs = ['templates', 'static', 'static/css', 'static/js', 'static/images']
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            print(f"❌ Missing directory: {dir_path}")
            print("Please run the setup script first.")
            sys.exit(1)
    
    # Check if required files exist
    required_files = [
        'templates/base.html',
        'templates/index.html',
        'static/css/style.css',
        'static/js/main.js'
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Missing file: {file_path}")
            print("Please ensure all template and static files are present.")
            sys.exit(1)
    
    print("✅ All required files and directories found")
    print("🚀 Starting server...")
    print("📱 Frontend: http://localhost:8000")
    print("🔧 API Docs: http://localhost:8000/docs")
    print("=" * 50)
    
    # Start the server
    try:
        uvicorn.run(
            "youtube:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down YouTube Video Downloader...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
