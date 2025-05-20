# VideoCapture: Cross-Platform Video Downloader

This document outlines the architecture and implementation details for VideoCapture, a lightweight cross-platform video downloader that captures screen content and audio across Windows, Linux, and macOS.

## Project Structure

```
videocapture/
├── src/
│   ├── core/              # Core components and shared utilities
│   ├── display_driver/    # Virtual display drivers for each platform  
│   ├── video_capture/     # Video capture implementations
│   ├── audio_loopback/    # Audio capture implementations
│   ├── sync/              # A/V synchronization module
│   ├── encoder/           # Video/audio encoding module
│   ├── muxer/             # Container format handling
│   ├── orchestration/     # Pipeline management
│   └── cli/               # Command-line interface
├── include/               # Public API headers
├── examples/              # Example usage code
├── tests/                 # Test suite
├── build/                 # Build artifacts
└── docs/                  # Documentation
```

## Core Architecture

The system is designed as a pipeline of interconnected modules, each handling a specific part of the capture, processing, and output workflow:

```
[Virtual Display] → [Video Capture] → [Sync Module] → [Encoder] → [Muxer] → [Output File]
      ↑                                    ↑
[Audio Loopback] ─────────────────────────┘
```

Data flows between modules via shared memory ring buffers for maximum performance, with each module running in its own thread.

## Module Details

### 1. Virtual Display Driver

Creates a virtual monitor that applications can render to, allowing for capture without visible output.

#### Windows Implementation
- Uses Windows Display Driver Model (WDDM) for driver integration
- Leverages OBS's virtual-display-capture SDK as reference
- Implements IDXGIOutputDuplication interface

#### Linux Implementation
- Uses v4l2loopback kernel module to create virtual video device
- Implements frame provider interface

#### macOS Implementation
- Uses CoreDisplay framework
- Creates virtual display via private APIs (requires SIP disable or signed driver)

### 2. Video Capture Module

Captures raw frames from the system's display or virtual display.

#### Windows Implementation
- Desktop Duplication API for capturing DirectX surfaces
- GDI capture fallback for compatibility

#### Linux Implementation
- X11: Uses XShm extension for shared memory transfer
- Wayland: Implements wlr-screencopy-unstable protocol
- Pipewire screen capture for Wayland fallback

#### macOS Implementation
- CGDisplayStream API for screen capture
- IOSurface for efficient memory handling

**Shared Memory Interface:**
```c
typedef struct {
    uint8_t *buffer;
    size_t size;
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    enum PixelFormat format;
    int64_t timestamp;
    bool keyframe;
} VideoFrame;

typedef struct {
    VideoFrame frames[RING_BUFFER_SIZE];
    atomic_int write_index;
    atomic_int read_index;
    pthread_mutex_t mutex;
    pthread_cond_t cond;
} VideoRingBuffer;
```

### 3. Audio Loopback Module

Captures system audio output without requiring hardware loopback.

#### Windows Implementation
- WASAPI (Windows Audio Session API) in loopback mode
- IAudioClient and IAudioCaptureClient interfaces

#### Linux Implementation
- PulseAudio monitor source capture
- ALSA loopback module as fallback

#### macOS Implementation
- CoreAudio with Audio Unit filters
- Implements custom loopback plugin

**Shared Memory Interface:**
```c
typedef struct {
    uint8_t *buffer;
    size_t size;
    uint32_t sample_rate;
    uint16_t channels;
    enum SampleFormat format;
    int64_t timestamp;
} AudioFrame;

typedef struct {
    AudioFrame frames[RING_BUFFER_SIZE];
    atomic_int write_index;
    atomic_int read_index;
    pthread_mutex_t mutex;
    pthread_cond_t cond;
} AudioRingBuffer;
```

### 4. Synchronization Module

Aligns video frames and audio samples to ensure proper synchronization.

- Maintains monotonic clock for reference timing
- Implements PTS (Presentation Time Stamp) calculation
- Handles drift correction via timestamp analysis
- Resamples audio or duplicates/drops video frames as needed

```c
typedef struct {
    int64_t base_time;
    double video_time_base;
    double audio_time_base;
    int64_t last_video_pts;
    int64_t last_audio_pts;
    double drift_threshold;
    pthread_mutex_t mutex;
} SyncContext;
```

### 5. Encoder Module

Compresses raw video and audio data using configurable codecs.

- Primary implementation uses FFmpeg's libavcodec
- Hardware acceleration support:
  - NVIDIA NVENC
  - Intel QuickSync
  - AMD AMF
  - VAAPI (Linux)
  - VideoToolbox (macOS)
- Configurable encoding parameters:
  - Bitrate control (CBR, VBR)
  - GOP (Group of Pictures) structure
  - Profile/Level selection
  - Preset (speed/quality tradeoff)

### 6. Muxer Module

Packages encoded video and audio streams into a container format.

- Uses libavformat for container handling
- Supports MP4 and MKV formats
- Maintains proper index tables for seeking
- Handles metadata insertion

### 7. Orchestration & CLI

Controls the overall pipeline and provides user interface.

- Dynamic pipeline configuration based on available hardware
- Thread management for each module
- Error handling and recovery strategies
- Performance monitoring
- Command-line interface with options:
  ```
  videocapture --output=file.mp4 --resolution=1920x1080 --fps=60 --vbitrate=5M --abitrate=192k --vcodec=h264 --acodec=aac --duration=60
  ```

## Integration & Data Flow

- Modules communicate via a plugin architecture with well-defined C API
- Ring buffers minimize copying between pipeline stages
- Zero-copy optimizations where hardware allows
- Event-based architecture for control messages

```c
typedef struct {
    void* (*init)(const char* config_json);
    int (*process)(void* context, void* input_buffer, void* output_buffer);
    void (*flush)(void* context);
    void (*destroy)(void* context);
} ModuleInterface;
```

## Platform-Specific Considerations

### Windows
- Driver signing requirements (test mode or EV certificate)
- User Account Control (UAC) elevation for driver installation
- DirectX version detection and compatibility

### Linux
- Package dependencies for development:
  - v4l2loopback-dkms
  - libpulse-dev
  - libx11-dev
  - libwayland-dev
- Permission handling for device access

### macOS
- Permissions for screen recording (TCC framework)
- Notarization requirements for distribution
- System Integrity Protection considerations

## DRM Protection Detection

- Windows: Checks for Protected Media Path (PMP) content
- macOS: Monitors CoreDisplay protection status
- Linux: Detects protected content via HDCP status

## Error Handling

- Graceful degradation when ideal capture method unavailable
- Detailed logging with severity levels
- Watchdog thread for deadlock detection

## Performance Considerations

- Memory pooling for frame buffers
- Worker thread pool for parallel processing
- GPU offloading where available
- Low-level optimizations (SIMD, intrinsics)

## Build Instructions

See the separate build document for platform-specific build instructions.
