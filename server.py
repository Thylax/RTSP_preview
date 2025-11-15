import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

# Configuration
RTSP_URL = "rtsp://localhost:8554/mystream"  # Change this to your RTSP stream URL
MJPEG_PORT = 8080  # Port for the web server
FRAME_RATE = 15  # Frames per second for MJPEG

class StreamHandler(BaseHTTPRequestHandler):
    ffmpeg_process = None
    
    def do_GET(self):
        if self.path == '/':
            # Serve the HTML page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>RTSP Stream Preview</title>
                <style>
                    * {
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }
                    
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #1a1a1a;
                        color: white;
                        height: 100vh;
                        overflow: hidden;
                    }
                    
                    .header {
                        background-color: #2a2a2a;
                        padding: 15px 20px;
                        border-bottom: 2px solid #333;
                    }
                    
                    .header h1 {
                        font-size: 24px;
                        font-weight: normal;
                    }
                    
                    .main-container {
                        display: flex;
                        height: calc(100vh - 60px);
                    }
                    
                    .sidebar {
                        width: 300px;
                        background-color: #2a2a2a;
                        border-right: 2px solid #333;
                        padding: 20px;
                        overflow-y: auto;
                    }
                    
                    .sidebar h2 {
                        font-size: 18px;
                        margin-bottom: 15px;
                        color: #888;
                    }
                    
                    .stream-list {
                        list-style: none;
                    }
                    
                    .stream-item {
                        padding: 12px 15px;
                        margin-bottom: 8px;
                        background-color: #1a1a1a;
                        border: 1px solid #333;
                        border-radius: 5px;
                        cursor: pointer;
                        transition: all 0.2s;
                    }
                    
                    .stream-item:hover {
                        background-color: #333;
                        border-color: #555;
                    }
                    
                    .stream-item.active {
                        background-color: #0066cc;
                        border-color: #0066cc;
                    }
                    
                    .stream-name {
                        font-weight: bold;
                        margin-bottom: 4px;
                    }
                    
                    .stream-url {
                        font-size: 12px;
                        color: #888;
                        word-break: break-all;
                    }
                    
                    .preview-container {
                        flex: 1;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        padding: 20px;
                    }
                    
                    .no-selection {
                        text-align: center;
                        color: #666;
                    }
                    
                    .no-selection h2 {
                        font-size: 24px;
                        margin-bottom: 10px;
                    }
                    
                    .video-container {
                        position: relative;
                        background-color: #000;
                        width: 100%;
                        max-width: 1200px;
                        display: none;
                    }
                    
                    .video-container.active {
                        display: block;
                    }
                    
                    .video-container img {
                        width: 100%;
                        height: auto;
                        display: block;
                    }
                    
                    .overlay {
                        position: absolute;
                        top: 10px;
                        left: 10px;
                        background-color: rgba(0, 0, 0, 0.7);
                        padding: 10px 15px;
                        border-radius: 5px;
                        font-size: 14px;
                    }
                    
                    .status {
                        color: #00ff00;
                        font-weight: bold;
                        margin-bottom: 5px;
                    }
                    
                    .stream-info {
                        margin-top: 15px;
                        padding: 15px;
                        background-color: #2a2a2a;
                        border-radius: 5px;
                        max-width: 1200px;
                        width: 100%;
                        display: none;
                    }
                    
                    .stream-info.active {
                        display: block;
                    }
                    
                    .stream-info h3 {
                        margin-bottom: 10px;
                        font-size: 16px;
                    }
                    
                    .stream-info p {
                        margin-bottom: 8px;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>RTSP Stream Preview System</h1>
                </div>
                
                <div class="main-container">
                    <!-- Sidebar with stream list -->
                    <div class="sidebar">
                        <h2>Available Streams</h2>
                        <ul class="stream-list" id="streamList">
                            <!-- Streams will be populated by JavaScript -->
                        </ul>
                    </div>
                    
                    <!-- Preview area -->
                    <div class="preview-container">
                        <div class="no-selection" id="noSelection">
                            <h2>No Stream Selected</h2>
                            <p>Select a stream from the list to begin preview</p>
                        </div>
                        
                        <div class="video-container" id="videoContainer">
                            <img id="streamImage" src="" alt="Stream Preview">
                            
                            <!-- Overlay Information -->
                            <div class="overlay">
                                <div class="status">● LIVE</div>
                                <div id="timestamp">--:--:--</div>
                                <div id="streamTitle">Stream 1</div>
                            </div>
                        </div>
                        
                        <div class="stream-info" id="streamInfo">
                            <h3>Stream Information</h3>
                            <p><strong>Source:</strong> <span id="infoSource">--</span></p>
                            <p><strong>Format:</strong> MJPEG</p>
                            <p><strong>Frame Rate:</strong> """ + str(FRAME_RATE) + """ fps</p>
                            <p><strong>Expected Latency:</strong> 0.2-1.0 seconds</p>
                        </div>
                    </div>
                </div>
                
                <script>
                    // Mock stream data (replace with actual streams later)
                    const streams = [
                        { id: 1, name: "Stream 1", url: "rtsp://192.168.1.100:8554/stream1" },
                        { id: 2, name: "Stream 2", url: "rtsp://192.168.1.100:8554/stream2" },
                        { id: 3, name: "Stream 3", url: "rtsp://192.168.1.100:8554/stream3" },
                        { id: 4, name: "Stream 4", url: "rtsp://192.168.1.100:8554/stream4" },
                        { id: 5, name: "SCADA Monitor 1", url: "rtsp://192.168.1.101:8554/scada1" },
                        { id: 6, name: "SCADA Monitor 2", url: "rtsp://192.168.1.101:8554/scada2" },
                    ];
                    
                    let selectedStream = null;
                    
                    // Populate stream list
                    function populateStreamList() {
                        const streamList = document.getElementById('streamList');
                        streamList.innerHTML = '';
                        
                        streams.forEach(stream => {
                            const li = document.createElement('li');
                            li.className = 'stream-item';
                            li.innerHTML = `
                                <div class="stream-name">${stream.name}</div>
                                <div class="stream-url">${stream.url}</div>
                            `;
                            li.onclick = () => selectStream(stream, li);
                            streamList.appendChild(li);
                        });
                    }
                    
                    // Select a stream
                    function selectStream(stream, element) {
                        // Update selection state
                        selectedStream = stream;
                        
                        // Update active class on list items
                        document.querySelectorAll('.stream-item').forEach(item => {
                            item.classList.remove('active');
                        });
                        element.classList.add('active');
                        
                        // Hide "no selection" message
                        document.getElementById('noSelection').style.display = 'none';
                        
                        // Show video container and info
                        document.getElementById('videoContainer').classList.add('active');
                        document.getElementById('streamInfo').classList.add('active');
                        
                        // Update stream info
                        document.getElementById('streamTitle').textContent = stream.name;
                        document.getElementById('infoSource').textContent = stream.url;
                        
                        // Update image source (for now, point to the MJPEG endpoint)
                        // Later you'll modify the server to handle multiple streams
                        document.getElementById('streamImage').src = '/stream.mjpeg';
                    }
                    
                    // Update timestamp every second
                    function updateTimestamp() {
                        const now = new Date();
                        const timeString = now.toLocaleTimeString();
                        document.getElementById('timestamp').textContent = timeString;
                    }
                    
                    // Initialize
                    populateStreamList();
                    updateTimestamp();
                    setInterval(updateTimestamp, 1000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        elif self.path == '/stream.mjpeg':
            # Serve the MJPEG stream
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            
            try:
                # Start FFmpeg process to convert RTSP to MJPEG
                cmd = [
                    'ffmpeg',
                    '-rtsp_transport', 'tcp',  # Use TCP for more reliable connection
                    '-timeout', '5000000',  # 5 second timeout in microseconds
                    '-stimeout', '5000000',  # Socket timeout
                    '-reconnect', '1',  # Enable reconnection
                    '-reconnect_streamed', '1',
                    '-reconnect_delay_max', '2',  # Max 2 seconds between reconnects
                    '-i', RTSP_URL,
                    '-f', 'mjpeg',
                    '-q:v', '5',  # Quality (2-31, lower is better)
                    '-r', str(FRAME_RATE),  # Frame rate
                    '-'  # Output to stdout
                ]
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=10**8
                )
                
                # Read and send MJPEG frames
                buffer = b''
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    
                    buffer += chunk
                    
                    # Look for JPEG frames in buffer
                    while True:
                        # Find JPEG start marker
                        start = buffer.find(b'\xff\xd8')
                        if start == -1:
                            break
                        
                        # Find JPEG end marker after start
                        end = buffer.find(b'\xff\xd9', start + 2)
                        if end == -1:
                            break
                        
                        # Extract frame
                        frame = buffer[start:end + 2]
                        buffer = buffer[end + 2:]
                        
                        # Send the frame
                        try:
                            self.wfile.write(b'--frame\r\n')
                            self.wfile.write(b'Content-Type: image/jpeg\r\n')
                            self.wfile.write(f'Content-Length: {len(frame)}\r\n\r\n'.encode())
                            self.wfile.write(frame)
                            self.wfile.write(b'\r\n')
                            self.wfile.flush()  # Force send immediately
                        except BrokenPipeError:
                            # Client disconnected
                            return
                    
            except Exception as e:
                print(f"Error streaming: {e}")
            finally:
                if process:
                    process.terminate()
    
    def log_message(self, format, *args):
        # Suppress log messages for cleaner output
        pass

def main():
    print("=" * 60)
    print("MJPEG Stream Server Starting...")
    print("=" * 60)
    print(f"RTSP Source: {RTSP_URL}")
    print(f"Server Port: {MJPEG_PORT}")
    print(f"Frame Rate: {FRAME_RATE} fps")
    print("=" * 60)
    
    # Check if FFmpeg is installed
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✓ FFmpeg is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ FFmpeg is not installed or not in PATH")
        print("\nPlease install FFmpeg:")
        print("  Download from: https://ffmpeg.org/download.html")
        print("  Or use: winget install ffmpeg")
        return
    
    print("\nServer ready!")
    print(f"\nOpen in browser: http://localhost:{MJPEG_PORT}")
    print(f"Or from another device: http://YOUR_DESKTOP_IP:{MJPEG_PORT}")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60)
    
    server = HTTPServer(('0.0.0.0', MJPEG_PORT), StreamHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.shutdown()

if __name__ == '__main__':
    main()