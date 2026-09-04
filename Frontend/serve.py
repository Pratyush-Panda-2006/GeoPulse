import http.server
import socketserver
import os
import sys
import io
from pathlib import Path

# Force UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PORT = 3000
DIRECTORY = Path(__file__).resolve().parent

class ThreadedHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

class CleanURLHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def translate_path(self, path):
        translated = super().translate_path(path)
        if os.path.exists(translated):
            return translated

        # Check if appending .html matches a file
        html_candidate = translated + ".html"
        if os.path.isfile(html_candidate):
            return html_candidate

        # Check if trailing slash trimmed + .html exists
        trimmed = translated.rstrip("\\/ ")
        if os.path.isfile(trimmed + ".html"):
            return trimmed + ".html"

        return translated

    def copyfile(self, source, outputfile):
        """Safely copy file bytes without crashing on client abort/disconnects."""
        try:
            super().copyfile(source, outputfile)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def log_message(self, format, *args):
        # Keep logs readable
        sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format % args))

def main():
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    with ThreadedHTTPServer(("", port), CleanURLHTTPRequestHandler) as httpd:
        print(f"GeoPulse Frontend server running at http://localhost:{port}")
        print(f"Serving directory: {DIRECTORY}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == "__main__":
    main()
