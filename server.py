import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

# Configuration
RTSP_URL = "rtsp://192.168.0.13:8554/desktop"  # Change this to your RTSP stream URL
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
                    body {
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        background-color: #1a1a1a;
                        color: white;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                    }
                    h1 {
                        text-align: center;
                    }
                    .video-container {
                        position: relative;
                        background-color: #000;
                        margin: 20px auto;
                        max-width: 960px;
                    }
                    img {
                        width: 100%;
                        height: auto;
                        display: block;
                    }
                    .overlay {
                        position: absolute;
                        top: 10px;
                        left: 10px;
                        background-color: rgba(0, 0, 0, 0.7);
                        padding: 10px;
                        border-radius: 5px;
                    }
                    .status {
                        color: #00ff00;
                        font-weight: bold;
                    }
                    .info {
                        margin-top: 20px;
                        padding: 15px;
                        background-color: #2a2a2a;
                        border-radius: 5px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>RTSP Stream Preview</h1>
                    
                    <div class="video-container">
                        <img src="/stream.mjpeg" alt="RTSP Stream">
                        
                        <!-- Overlay Information -->
                        <div class="overlay">
                            <div class="status">● LIVE</div>
                            <div id="timestamp">--:--:--</div>
                            <div>Latency Test: Move mouse to check delay</div>
                        </div>
                    </div>
                    
                    <div class="info">
                        <h3>Stream Information</h3>
                        <p><strong>Source:</strong> """ + RTSP_URL + """</p>
                        <p><strong>Format:</strong> MJPEG</p>
                        <p><strong>Frame Rate:</strong> """ + str(FRAME_RATE) + """ fps</p>
                        <p><strong>Expected Latency:</strong> 0.2-1.0 seconds</p>
                    </div>
                </div>
                
                <script>
                    // Update timestamp every second
                    function updateTimestamp() {
                        const now = new Date();
                        const timeString = now.toLocaleTimeString();
                        document.getElementById('timestamp').textContent = timeString;
                    }
                    
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
                while True:
                    # Read until we find the JPEG start marker
                    data = b''
                    while True:
                        byte = process.stdout.read(1)
                        if not byte:
                            return
                        data += byte
                        if len(data) >= 2 and data[-2:] == b'\xff\xd8':  # JPEG start
                            data = b'\xff\xd8'
                            break
                    
                    # Read until we find the JPEG end marker
                    while True:
                        byte = process.stdout.read(1)
                        if not byte:
                            return
                        data += byte
                        if len(data) >= 2 and data[-2:] == b'\xff\xd9':  # JPEG end
                            break
                    
                    # Send the frame
                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(data)}\r\n\r\n'.encode())
                    self.wfile.write(data)
                    self.wfile.write(b'\r\n')
                    
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