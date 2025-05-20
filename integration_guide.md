# Video Downloader - Integration Guide

This guide explains how to build, install, and integrate the VideoDownloader library into your applications.

## Table of Contents

1. [Overview](#overview)
2. [Building the C++ Library](#building-the-c-library)
3. [Python Integration](#python-integration)
4. [Web Application Integration](#web-application-integration)
5. [Advanced Usage](#advanced-usage)
6. [Troubleshooting](#troubleshooting)

## Overview

The VideoDownloader project consists of:

- **Core C++ Library** - Handles the actual video downloading functionality
- **Python Bindings** - Allows Python programs to use the library
- **Web Interface** - A browser-based UI for downloading videos

## Building the C++ Library

### Prerequisites

- CMake 3.10 or higher
- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2019+)
- libcurl development package

#### Installing prerequisites on Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install build-essential cmake libcurl4-openssl-dev
```

#### Installing prerequisites on macOS:

```bash
brew install cmake curl
```

#### Installing prerequisites on Windows:

1. Install Visual Studio with C++ development tools
2. Install CMake from https://cmake.org/download/
3. Install vcpkg and libcurl:
   ```
   git clone https://github.com/Microsoft/vcpkg.git
   cd vcpkg
   .\bootstrap-vcpkg.bat
   .\vcpkg install curl:x64-windows
   ```

### Building

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/video-downloader.git
   cd video-downloader
   ```

2. Create a build directory:
   ```bash
   mkdir build
   cd build
   ```

3. Configure with CMake:
   ```bash
   # Linux/macOS
   cmake ..
   
   # Windows with vcpkg
   cmake -DCMAKE_TOOLCHAIN_FILE=[path_to_vcpkg]/scripts/buildsystems/vcpkg.cmake ..
   ```

4. Build the library:
   ```bash
   cmake --build .
   ```

5. Install:
   ```bash
   # You may need sudo on Linux
   cmake --install .
   ```

## Python Integration

### Building the Python Wrapper

The Python wrapper is built automatically when you build the C++ library, but you need to ensure it's accessible to Python.

1. Copy the built library files to your Python project or a directory in your Python path:
   ```bash
   # Linux/macOS
   cp libvideodownloader.so /path/to/your/python/project/
   
   # Windows
   copy videodownloader.dll C:\path\to\your\python\project\
   ```

2. Install the Python wrapper:
   ```bash
   # From the project root
   pip install -e .
   ```

### Using the Python Wrapper

```python
from video_downloader import VideoDownloader

# Create an instance
downloader = VideoDownloader()

# Download a video
url = "https://example.com/sample-video.mp4"
output_path = "downloaded_video.mp4"

# Optional progress callback
def show_progress(progress):
    print(f"Progress: {progress*100:.1f}%")

# Start download
success = downloader.download_video(url, output_path, show_progress)

if success:
    print(f"Video downloaded successfully to {output_path}")
else:
    print(f"Download failed: {downloader.get_last_error()}")
```

## Web Application Integration

### Setting Up the Web Backend

1. Create a backend API service using Flask, Express, or your preferred framework
2. Set up endpoints to interface with the VideoDownloader library

Example Flask backend:

```python
from flask import Flask, request, jsonify
from video_downloader import VideoDownloader
import os
import threading

app = Flask(__name__)
download_jobs = {}  # Store download progress info

@app.route('/api/analyze', methods=['POST'])
def analyze_url():
    url = request.json.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
        
    try:
        downloader = VideoDownloader()
        formats = downloader.get_available_formats(url)
        return jsonify({'formats': formats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def start_download():
    url = request.json.get('url')
    format_name = request.json.get('format')
    filename = request.json.get('filename', 'video')
    
    if not url or not format_name:
        return jsonify({'error': 'URL and format are required'}), 400
    
    # Generate job ID
    job_id = os.urandom(8).hex()
    download_jobs[job_id] = {'progress': 0, 'status': 'starting'}
    
    # Start download in background thread
    def download_task():
        try:
            downloader = VideoDownloader()
            
            # Extract format and quality from format string (e.g., "mp4-720p")
            parts = format_name.split('-')
            if len(parts) >= 2:
                downloader.set_preferred_format(parts[0])
                downloader.set_preferred_quality(parts[1])
            
            # Set up progress callback
            def progress_callback(progress):
                download_jobs[job_id]['progress'] = progress
                
            # Ensure output filename has extension
            if '.' not in filename:
                ext = downloader.get_preferred_format() or 'mp4'
                output_path = f"{filename}.{ext}"
            else:
                output_path = filename
                
            # Start download
            download_jobs[job_id]['status'] = 'downloading'
            success = downloader.download_video(url, output_path, progress_callback)
            
            if success:
                download_jobs[job_id]['status'] = 'completed'
            else:
                download_jobs[job_id]['status'] = 'failed'
                download_jobs[job_id]['error'] = downloader.get_last_error()
        except Exception as e:
            download_jobs[job_id]['status'] = 'failed'
            download_jobs[job_id]['error'] = str(e)
    
    # Start the download thread
    thread = threading.Thread(target=download_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'started'
    })

@app.route('/api/status/<job_id>', methods=['GET'])
def check_status(job_id):
    if job_id not in download_jobs:
        return jsonify({'error': 'Job not found'}), 404
        
    return jsonify(download_jobs[job_id])

if __name__ == '__main__':
    app.run(debug=True)
```

### Connecting the Web Frontend

1. Serve the HTML/CSS/JS files from your web server
2. Update the JavaScript to call your backend API endpoints

## Advanced Usage

### Custom Format Selection

The VideoDownloader library allows you to specify preferred formats and quality:

```cpp
// C++ Usage
VideoDownloader downloader;
downloader.setPreferredFormat("mp4");
downloader.setPreferredQuality("720p");
```

```python
# Python Usage
downloader = VideoDownloader()
downloader.set_preferred_format("mp4")
downloader.set_preferred_quality("720p")
```

### Handling Rate Limits

Some video platforms implement rate limiting. Add delay between requests if you're downloading multiple videos:

```python
import time

for url in video_urls:
    downloader.download_video(url, f"video_{i}.mp4")
    time.sleep(2)  # Wait 2 seconds between downloads
```

## Troubleshooting

### Common Issues

#### Library Not Found

Error: `Could not load VideoDownloader library`

Solutions:
- Ensure the library is in your system's library path or the same directory as your script
- Check file permissions
- Verify that the library was built with the correct architecture (32-bit vs 64-bit)

#### Download Failures

If downloads fail with specific error messages:

- "Failed to initialize CURL" - Check that libcurl is properly installed
- "URL not supported" - The library may not support the specific video platform
- "Network error" - Check your internet connection or proxy settings

#### Building Issues

If you encounter build errors:

- Make sure all dependencies are installed
- Check compiler compatibility
- Review CMake output for detailed error messages

For additional help, please file an issue on the project's repository with detailed information about your problem.
