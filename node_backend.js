// server.js
const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');
const ffi = require('ffi-napi');
const ref = require('ref-napi');
const bodyParser = require('body-parser');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// Configure download directory
const DOWNLOAD_DIR = path.join(__dirname, 'downloads');
if (!fs.existsSync(DOWNLOAD_DIR)) {
  fs.mkdirSync(DOWNLOAD_DIR);
}

// Track active downloads
const activeDownloads = new Map();

// Load the VideoDownloader library using FFI
let libPath;
if (process.platform === 'win32') {
  libPath = path.join(__dirname, 'lib', 'videodownloader.dll');
} else if (process.platform === 'darwin') {
  libPath = path.join(__dirname, 'lib', 'libvideodownloader.dylib');
} else {
  libPath = path.join(__dirname, 'lib', 'libvideodownloader.so');
}

// Define the FFI interface
const voidPtr = ref.refType(ref.types.void);
const stringPtr = ref.refType(ref.types.CString);
const intPtr = ref.refType(ref.types.int);

// Callback type for progress function
const ProgressCallback = ffi.Callback(
  'void', ['double'],
  (progress) => {
    // This will be defined per download job
  }
);

// Define the library interface
const VideoDownloaderLib = ffi.Library(libPath, {
  'VideoDownloader_Create': ['pointer', []],
  'VideoDownloader_Destroy': ['void', ['pointer']],
  'VideoDownloader_DownloadVideo': ['bool', ['pointer', 'string', 'string', 'pointer', 'pointer']],
  'VideoDownloader_GetAvailableFormats': ['void', ['pointer', 'string', stringPtr, intPtr]],
  'VideoDownloader_FreeFormats': ['void', [stringPtr, 'int']],
  'VideoDownloader_SetPreferredFormat': ['void', ['pointer', 'string']],
  'VideoDownloader_SetPreferredQuality': ['void', ['pointer', 'string']],
  'VideoDownloader_GetLastError': ['string', ['pointer']],
  'VideoDownloader_GetVersion': ['string', []]
});

// API endpoints
app.get('/api/version', (req, res) => {
  try {
    const version = VideoDownloaderLib.VideoDownloader_GetVersion();
    res.json({ version });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/analyze', (req, res) => {
  const { url } = req.body;
  
  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }
  
  try {
    // For demonstration, we'll return mock formats
    // In a real implementation, we would call the C++ library to analyze the URL
    
    // Mock implementation
    const mockFormats = [
      'mp4-360p',
      'mp4-720p',
      'mp4-1080p',
      'webm-360p',
      'webm-720p',
      'webm-1080p'
    ];
    
    // Create a fake delay to simulate processing
    setTimeout(() => {
      res.json({ formats: mockFormats });
    }, 1000);
    
    /* Real implementation would look like this:
    const downloader = VideoDownloaderLib.VideoDownloader_Create();
    
    // This part is tricky with FFI and would require more complex code
    // to handle the string array returned by the C++ library
    // This is a simplified version
    
    const formatsPtr = ref.alloc(stringPtr);
    const countPtr = ref.alloc('int');
    
    VideoDownloaderLib.VideoDownloader_GetAvailableFormats(
      downloader, 
      url, 
      formatsPtr,
      countPtr
    );
    
    // Process the formats...
    
    VideoDownloaderLib.VideoDownloader_Destroy(downloader);
    */
    
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/download', (req, res) => {
  const { url, format, filename } = req.body;
  
  if (!url || !format) {
    return res.status(400).json({ error: 'URL and format are required' });
  }
  
  try {
    // Generate a unique ID for this download
    const downloadId = uuidv4();
    
    // Determine output filename
    let outputFilename = filename || 'video';
    const formatParts = format.split('-');
    if (formatParts.length > 0 && !outputFilename.includes('.')) {
      outputFilename += '.' + formatParts[0];
    }
    
    const outputPath = path.join(DOWNLOAD_DIR, outputFilename);
    
    // Create download job object
    const downloadJob = {
      id: downloadId,
      url,
      format,
      outputPath,
      progress: 0,
      status: 'starting',
      error: null,
      startTime: Date.now()
    };
    
    // Store in active downloads
    activeDownloads.set(downloadId, downloadJob);
    
    // Start the download in a separate process to avoid blocking
    const pythonScript = path.join(__dirname, 'scripts', 'download_video.py');
    
    const process = spawn('python', [
      pythonScript,
      '--url', url,
      '--format', format,
      '--output', outputPath
    ]);
    
    process.stdout.on('data', (data) => {
      const output = data.toString().trim();
      
      // Parse progress updates from the Python script
      if (output.startsWith('PROGRESS:')) {
        const progress = parseFloat(output.split(':')[1]);
        downloadJob.progress = progress;
      }
    });
    
    process.stderr.on('data', (data) => {
      downloadJob.error = data.toString().trim();
      downloadJob.status = 'error';
    });
    
    process.on('close', (code) => {
      if (code === 0) {
        downloadJob.status = 'completed';
        downloadJob.progress = 1.0;
      } else {
        downloadJob.status = 'failed';
        if (!downloadJob.error) {
          downloadJob.error = `Process exited with code ${code}`;
        }
      }
    });
    
    /* Alternative implementation using FFI directly (more efficient but more complex):
    
    // Create downloader instance
    const downloader = VideoDownloaderLib.VideoDownloader_Create();
    
    // Set format preferences
    if (formatParts.length >= 2) {
      VideoDownloaderLib.VideoDownloader_SetPreferredFormat(downloader, formatParts[0]);
      VideoDownloaderLib.VideoDownloader_SetPreferredQuality(downloader, formatParts[1]);
    }
    
    // Set up progress callback
    const progressCallback = ffi.Callback(
      'void', ['double'],
      (progress) => {
        downloadJob.progress = progress;
      }
    );
    
    // Start download in a separate thread to avoid blocking Node.js event loop
    setImmediate(() => {
      try {
        downloadJob.status = 'downloading';
        
        const success = VideoDownloaderLib.VideoDownloader_DownloadVideo(
          downloader,
          url,
          outputPath,
          progressCallback,
          null
        );
        
        if (success) {
          downloadJob.status = 'completed';
          downloadJob.progress = 1.0;
        } else {
          downloadJob.status = 'failed';
          downloadJob.error = VideoDownloaderLib.VideoDownloader_GetLastError(downloader);
        }
      } catch (err) {
        downloadJob.status = 'failed';
        downloadJob.error = err.message;
      } finally {
        VideoDownloaderLib.VideoDownloader_Destroy(downloader);
      }
    });
    */
    
    // Return the download ID to the client
    res.json({
      id: downloadId,
      status: 'started',
      filename: outputFilename
    });
    
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/download/:id/status', (req, res) => {
  const downloadId = req.params.id;
  
  if (!activeDownloads.has(downloadId)) {
    return res.status(404).json({ error: 'Download not found' });
  }
  
  const download = activeDownloads.get(downloadId);
  res.json({
    id: download.id,
    progress: download.progress,
    status: download.status,
    error: download.error
  });
});

app.get('/api/download/:id/file', (req, res) => {
  const downloadId = req.params.id;
  
  if (!activeDownloads.has(downloadId)) {
    return res.status(404).json({ error: 'Download not found' });
  }
  
  const download = activeDownloads.get(downloadId);
  
  if (download.status !== 'completed') {
    return res.status(400).json({ error: 'Download is not completed yet' });
  }
  
  res.download(download.outputPath);
});

// Clean up old downloads periodically (keep for 1 hour)
setInterval(() => {
  const now = Date.now();
  for (const [id, download] of activeDownloads.entries()) {
    const age = now - download.startTime;
    if (age > 60 * 60 * 1000) { // 1 hour
      activeDownloads.delete(id);
      
      // Delete the file if it exists
      if (download.status === 'completed' && fs.existsSync(download.outputPath)) {
        fs.unlinkSync(download.outputPath);
      }
    }
  }
}, 15 * 60 * 1000); // Run every 15 minutes

// Start the server
app.listen(port, () => {
  console.log(`Video Downloader API running on port ${port}`);
});
