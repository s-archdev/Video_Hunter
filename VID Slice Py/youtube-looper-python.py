from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import sys
import webbrowser
from pathlib import Path

# Configuration
PORT = 8000
HTML_FILENAME = "youtube_looper.html"

def create_html_file():
    """Create the HTML file with YouTube looper functionality"""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Video Looper</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .video-container {
            position: relative;
            width: 100%;
            padding-bottom: 56.25%; /* 16:9 Aspect Ratio */
            height: 0;
        }
        .video-container iframe {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
            padding: 15px;
            background-color: #f5f5f5;
            border-radius: 5px;
        }
        .input-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        label {
            font-weight: bold;
            font-size: 14px;
        }
        input[type="text"] {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 180px;
        }
        input[type="number"] {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 80px;
        }
        button {
            padding: 8px 16px;
            background-color: #4285f4;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background-color: #3367d6;
        }
        .status {
            font-size: 14px;
            color: #555;
        }
        .active {
            background-color: #34a853;
        }
        .slider-container {
            display: flex;
            flex-direction: column;
            width: 100%;
            gap: 5px;
        }
        .slider-labels {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
        }
        .slider {
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>YouTube Video Looper</h1>
        
        <div class="controls">
            <div class="input-group">
                <label for="video-url">YouTube URL or Video ID</label>
                <input type="text" id="video-url" placeholder="https://www.youtube.com/watch?v=..." value="dQw4w9WgXcQ">
            </div>
            <button id="load-video">Load Video</button>
        </div>
        
        <div class="video-container">
            <div id="player"></div>
        </div>
        
        <div class="controls">
            <div class="input-group">
                <label for="start-time">Start Time (seconds)</label>
                <input type="number" id="start-time" min="0" step="0.1" value="0">
            </div>
            <div class="input-group">
                <label for="end-time">End Time (seconds)</label>
                <input type="number" id="end-time" min="0" step="0.1" value="10">
            </div>
            <button id="toggle-loop">Start Loop</button>
            <button id="play-pause">Play</button>
            <div class="status" id="status">Ready</div>
        </div>
        
        <div class="slider-container">
            <input type="range" min="0" max="100" value="0" class="slider" id="progress-slider">
            <div class="slider-labels">
                <span id="current-time">0:00</span>
                <span id="duration">0:00</span>
            </div>
        </div>
    </div>

    <script>
        // YouTube API integration
        let player;
        let looping = false;
        let loopInterval;
        let videoLoaded = false;
        
        // Load YouTube API
        const tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        const firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        
        // Initialize player when API is ready
        window.onYouTubeIframeAPIReady = function() {
            const videoId = getVideoIdFromInput();
            player = new YT.Player('player', {
                height: '100%',
                width: '100%',
                videoId: videoId,
                playerVars: {
                    'playsinline': 1,
                    'rel': 0,
                    'modestbranding': 1
                },
                events: {
                    'onReady': onPlayerReady,
                    'onStateChange': onPlayerStateChange
                }
            });
        };
        
        // Function to extract video ID from various YouTube URL formats
        function extractVideoId(url) {
            if (!url) return null;
            
            // Check if it's already just an ID (no slashes or dots)
            if (!/[\/\.]/.test(url) && url.length > 8) {
                return url;
            }
            
            const regExp = /^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
            const match = url.match(regExp);
            return (match && match[2].length === 11) ? match[2] : null;
        }
        
        function getVideoIdFromInput() {
            const input = document.getElementById('video-url').value.trim();
            return extractVideoId(input) || 'dQw4w9WgXcQ'; // Default video if invalid
        }
        
        // Player ready event
        function onPlayerReady(event) {
            updateVideoDuration();
            videoLoaded = true;
            document.getElementById('status').textContent = 'Video loaded';
            updatePlayPauseButton();
        }
        
        // Player state change event
        function onPlayerStateChange(event) {
            if (event.data === YT.PlayerState.ENDED && !looping) {
                player.seekTo(0);
                player.playVideo();
            }
            updatePlayPauseButton();
        }
        
        // Format time as MM:SS
        function formatTime(seconds) {
            const min = Math.floor(seconds / 60);
            const sec = Math.floor(seconds % 60).toString().padStart(2, '0');
            return `${min}:${sec}`;
        }
        
        // Update video duration display
        function updateVideoDuration() {
            const duration = player.getDuration();
            document.getElementById('duration').textContent = formatTime(duration);
            document.getElementById('end-time').value = duration.toFixed(1);
            
            // Update slider max value
            document.getElementById('progress-slider').max = duration;
        }
        
        // Update current time display and slider
        function updateTimeDisplay() {
            if (!videoLoaded) return;
            
            const currentTime = player.getCurrentTime();
            document.getElementById('current-time').textContent = formatTime(currentTime);
            
            // Update slider without triggering the input event
            const slider = document.getElementById('progress-slider');
            slider.value = currentTime;
        }
        
        // Start/stop the loop
        function toggleLoop() {
            const loopButton = document.getElementById('toggle-loop');
            
            if (looping) {
                // Stop looping
                clearInterval(loopInterval);
                looping = false;
                loopButton.textContent = 'Start Loop';
                loopButton.classList.remove('active');
                document.getElementById('status').textContent = 'Loop stopped';
            } else {
                // Start looping
                const startTime = parseFloat(document.getElementById('start-time').value);
                const endTime = parseFloat(document.getElementById('end-time').value);
                
                if (startTime >= endTime) {
                    document.getElementById('status').textContent = 'Error: Start time must be less than end time';
                    return;
                }
                
                player.seekTo(startTime);
                player.playVideo();
                
                loopInterval = setInterval(() => {
                    if (!videoLoaded) return;
                    
                    const currentTime = player.getCurrentTime();
                    if (currentTime >= endTime) {
                        player.seekTo(startTime);
                    }
                }, 100);
                
                looping = true;
                loopButton.textContent = 'Stop Loop';
                loopButton.classList.add('active');
                document.getElementById('status').textContent = `Looping from ${startTime}s to ${endTime}s`;
            }
        }
        
        // Update play/pause button based on player state
        function updatePlayPauseButton() {
            const button = document.getElementById('play-pause');
            if (!videoLoaded) return;
            
            const state = player.getPlayerState();
            if (state === YT.PlayerState.PLAYING) {
                button.textContent = 'Pause';
            } else {
                button.textContent = 'Play';
            }
        }
        
        // Toggle play/pause
        function togglePlayPause() {
            if (!videoLoaded) return;
            
            const state = player.getPlayerState();
            if (state === YT.PlayerState.PLAYING) {
                player.pauseVideo();
            } else {
                player.playVideo();
            }
        }
        
        // Load a new video
        function loadVideo() {
            const videoId = getVideoIdFromInput();
            if (!videoId) {
                document.getElementById('status').textContent = 'Error: Invalid YouTube URL or ID';
                return;
            }
            
            // Stop current loop if running
            if (looping) {
                toggleLoop();
            }
            
            player.loadVideoById(videoId);
            document.getElementById('status').textContent = 'Loading video...';
            
            // Reset time inputs
            document.getElementById('start-time').value = '0';
            
            // Update duration after a slight delay to ensure video is loaded
            setTimeout(updateVideoDuration, 1000);
        }
        
        // Initialize and set up event listeners
        document.addEventListener('DOMContentLoaded', () => {
            // Set up button event listeners
            document.getElementById('toggle-loop').addEventListener('click', toggleLoop);
            document.getElementById('play-pause').addEventListener('click', togglePlayPause);
            document.getElementById('load-video').addEventListener('click', loadVideo);
            
            // Set up progress slider
            const slider = document.getElementById('progress-slider');
            slider.addEventListener('input', () => {
                if (!videoLoaded) return;
                player.seekTo(parseFloat(slider.value));
            });
            
            // Update time display every 100ms
            setInterval(updateTimeDisplay, 100);
        });
    </script>
</body>
</html>"""
    
    with open(HTML_FILENAME, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return Path(HTML_FILENAME).absolute()

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def start_server():
    """Start a simple HTTP server"""
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, CustomHTTPRequestHandler)
    print(f"Server running at http://localhost:{PORT}/")
    print(f"YouTube Looper available at http://localhost:{PORT}/{HTML_FILENAME}")
    print("Press Ctrl+C to stop the server")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

def main():
    """Main function"""
    # Create the HTML file
    html_path = create_html_file()
    print(f"Created HTML file: {html_path}")
    
    # Open the HTML file in the default browser
    webbrowser.open(f'http://localhost:{PORT}/{HTML_FILENAME}')
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()