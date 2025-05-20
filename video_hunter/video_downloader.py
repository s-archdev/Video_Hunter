import sys
import os
import re
import yt_dlp
import argparse
from tqdm import tqdm

class VideoDownloader:
    def __init__(self, output_dir="downloads"):
        """Initialize the video downloader with an output directory."""
        self.output_dir = output_dir
        
        # Create the output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def extract_video(self, url):
        """Download a video from the given URL."""
        try:
            # Configuration options for yt-dlp
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Get best quality
                'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),  # Output file template
                'restrictfilenames': True,  # Restrict filenames to ASCII characters
                'noplaylist': True,  # Download only the video if URL refers to a playlist
                'progress_hooks': [self._progress_hook],  # Display download progress
                'merge_output_format': 'mp4',  # Merge video and audio into mp4
            }
            
            print(f"Extracting video from: {url}")
            
            # Create a yt-dlp instance with our options
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info before downloading
                info_dict = ydl.extract_info(url, download=False)
                video_title = info_dict.get('title', 'video')
                
                print(f"Title: {video_title}")
                print(f"Duration: {self._format_duration(info_dict.get('duration', 0))}")
                print(f"Resolution: {info_dict.get('width', 'unknown')}x{info_dict.get('height', 'unknown')}")
                
                # Download the video
                ydl.download([url])
                
                # Return path to downloaded file
                filename = ydl.prepare_filename(info_dict)
                return filename
                
        except Exception as e:
            print(f"Error downloading video: {str(e)}")
            return None
    
    def _progress_hook(self, d):
        """Display download progress."""
        if d['status'] == 'downloading':
            # Display a simple progress indicator
            percent = d.get('_percent_str', 'unknown')
            speed = d.get('_speed_str', 'unknown speed')
            eta = d.get('_eta_str', 'unknown ETA')
            print(f"\rDownloading... {percent} at {speed}, ETA: {eta}", end='')
        
        elif d['status'] == 'finished':
            print("\nDownload complete! Converting format...")
    
    def _format_duration(self, seconds):
        """Format seconds into HH:MM:SS."""
        if not seconds:
            return "unknown"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"


def validate_url(url):
    """Validate that the URL has a common video domain or appears to be a video URL."""
    video_domains = [
        'youtube.com', 'youtu.be', 
        'vimeo.com', 
        'dailymotion.com', 
        'facebook.com/watch', 
        'twitch.tv',
        'tiktok.com',
        'instagram.com',
        'twitter.com', 'x.com'
    ]
    
    # Check if the URL contains a known video domain
    for domain in video_domains:
        if domain in url:
            return True
    
    # Check if the URL appears to be a video file
    video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm']
    for ext in video_extensions:
        if url.endswith(ext):
            return True
    
    # If we're not sure, we'll let yt-dlp try anyway
    return True


def main():
    parser = argparse.ArgumentParser(description='Download videos from URLs')
    parser.add_argument('url', help='URL of the video to download')
    parser.add_argument('--output-dir', '-o', default='downloads', help='Directory to save downloads')
    
    args = parser.parse_args()
    
    # Validate the URL
    if not validate_url(args.url):
        print("Warning: This URL doesn't appear to be from a common video site.")
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    # Create downloader and extract video
    downloader = VideoDownloader(output_dir=args.output_dir)
    output_file = downloader.extract_video(args.url)
    
    if output_file:
        print(f"\nVideo successfully downloaded to: {output_file}")
    else:
        print("\nFailed to download video.")


if __name__ == "__main__":
    main()
