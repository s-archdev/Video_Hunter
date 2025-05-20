# video_downloader.py
import ctypes
import os
from typing import Callable, List, Optional
import platform

class VideoDownloader:
    """
    Python wrapper for the VideoDownloader C++ library
    """
    
    def __init__(self):
        """
        Initialize the VideoDownloader wrapper and load the native library
        """
        # Determine the appropriate library file extension based on the platform
        if platform.system() == "Windows":
            lib_name = "videodownloader.dll"
        elif platform.system() == "Darwin":  # macOS
            lib_name = "libvideodownloader.dylib"
        else:  # Linux and others
            lib_name = "libvideodownloader.so"
            
        # Try to load from standard locations
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            lib_path = os.path.join(current_dir, lib_name)
            self._lib = ctypes.CDLL(lib_path)
        except OSError:
            # If not found in the current directory, try system paths
            try:
                self._lib = ctypes.CDLL(lib_name)
            except OSError as e:
                raise RuntimeError(f"Could not load VideoDownloader library: {e}")
        
        # Define function prototypes
        self._define_function_prototypes()
        
        # Create a new instance of the C++ VideoDownloader
        self._downloader = self._lib.VideoDownloader_Create()
        
    def _define_function_prototypes(self):
        """
        Define the function prototypes for the C++ library functions
        """
        # Create/destroy instance
        self._lib.VideoDownloader_Create.restype = ctypes.c_void_p
        self._lib.VideoDownloader_Destroy.argtypes = [ctypes.c_void_p]
        
        # Download video
        self._lib.VideoDownloader_DownloadVideo.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_void_p,
            ctypes.c_void_p
        ]
        self._lib.VideoDownloader_DownloadVideo.restype = ctypes.c_bool
        
        # Get available formats
        self._lib.VideoDownloader_GetAvailableFormats.argtypes = [
            ctypes.c_void_p, 
            ctypes.c_char_p, 
            ctypes.POINTER(ctypes.c_char_p), 
            ctypes.POINTER(ctypes.c_int)
        ]
        
        # Set format/quality
        self._lib.VideoDownloader_SetPreferredFormat.argtypes = [
            ctypes.c_void_p, 
            ctypes.c_char_p
        ]
        self._lib.VideoDownloader_SetPreferredQuality.argtypes = [
            ctypes.c_void_p, 
            ctypes.c_char_p
        ]
        
        # Get last error
        self._lib.VideoDownloader_GetLastError.argtypes = [ctypes.c_void_p]
        self._lib.VideoDownloader_GetLastError.restype = ctypes.c_char_p
        
        # Get version
        self._lib.VideoDownloader_GetVersion.restype = ctypes.c_char_p
        
    def __del__(self):
        """
        Clean up the C++ VideoDownloader instance
        """
        if hasattr(self, '_lib') and hasattr(self, '_downloader'):
            self._lib.VideoDownloader_Destroy(self._downloader)
            
    def download_video(self, url: str, output_path: str, 
                       progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """
        Download a video from a URL to a local file
        
        Args:
            url: Source URL of the video
            output_path: Local path where the video will be saved
            progress_callback: Optional callback to monitor download progress (0.0 to 1.0)
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        # Progress callback handling with ctypes
        callback_func = None
        if progress_callback:
            PROGRESS_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_double)
            
            def callback_wrapper(progress):
                progress_callback(progress)
                
            callback_func = PROGRESS_CALLBACK(callback_wrapper)
        
        result = self._lib.VideoDownloader_DownloadVideo(
            self._downloader,
            url.encode('utf-8'),
            output_path.encode('utf-8'),
            callback_func,
            None  # User data pointer, not needed for this wrapper
        )
        
        return result
        
    def get_available_formats(self, url: str) -> List[str]:
        """
        Get available video formats from a URL
        
        Args:
            url: Source URL to check for video formats
            
        Returns:
            List[str]: List of format descriptions (e.g. "mp4-720p", "webm-1080p")
        """
        formats_ptr = ctypes.POINTER(ctypes.c_char_p)()
        count = ctypes.c_int(0)
        
        self._lib.VideoDownloader_GetAvailableFormats(
            self._downloader,
            url.encode('utf-8'),
            ctypes.byref(formats_ptr),
            ctypes.byref(count)
        )
        
        # Convert C string array to Python list
        formats = []
        for i in range(count.value):
            format_str = formats_ptr[i].decode('utf-8')
            formats.append(format_str)
            
        # Free memory allocated by C++
        self._lib.VideoDownloader_FreeFormats(formats_ptr, count)
        
        return formats
        
    def set_preferred_format(self, format_name: str) -> None:
        """
        Set preferred video format
        
        Args:
            format_name: Format identifier (e.g. "mp4", "webm")
        """
        self._lib.VideoDownloader_SetPreferredFormat(
            self._downloader,
            format_name.encode('utf-8')
        )
        
    def set_preferred_quality(self, quality: str) -> None:
        """
        Set preferred video quality
        
        Args:
            quality: Quality identifier (e.g. "720p", "1080p")
        """
        self._lib.VideoDownloader_SetPreferredQuality(
            self._downloader,
            quality.encode('utf-8')
        )
        
    def get_last_error(self) -> str:
        """
        Get last error message if a download failed
        
        Returns:
            str: Error message
        """
        error_msg = self._lib.VideoDownloader_GetLastError(self._downloader)
        return error_msg.decode('utf-8') if error_msg else ""
        
    @staticmethod
    def get_version() -> str:
        """
        Get library version
        
        Returns:
            str: Version string
        """
        version = VideoDownloader._lib.VideoDownloader_GetVersion()
        return version.decode('utf-8')


# Example usage
if __name__ == "__main__":
    # Example progress callback
    def show_progress(progress):
        print(f"Download progress: {progress*100:.1f}%")
    
    try:
        # Create downloader instance
        downloader = VideoDownloader()
        
        # Set preferences
        downloader.set_preferred_format("mp4")
        downloader.set_preferred_quality("720p")
        
        # Download a video
        video_url = "https://example.com/sample-video.mp4"
        output_path = "downloaded_video.mp4"
        
        print(f"Downloading video from {video_url}...")
        success = downloader.download_video(video_url, output_path, show_progress)
        
        if success:
            print(f"Video successfully downloaded to {output_path}")
        else:
            print(f"Download failed: {downloader.get_last_error()}")
            
        # Get available formats
        formats = downloader.get_available_formats(video_url)
        print("Available formats:")
        for fmt in formats:
            print(f"  - {fmt}")
            
    except Exception as e:
        print(f"Error: {e}")
