#!/usr/bin/env python3
import http.server
import socketserver
import os
import time
import threading
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8000
RELOAD_PATH = "/__reload__"
WATCH_EXTENSIONS = {".html", ".css", ".js", ".yml", ".yaml"}
CLIENTS = []
CLIENTS_LOCK = threading.Lock()

INJECT_SCRIPT = b"""
<script>
const evtSource = new EventSource('/__reload__');
evtSource.onmessage = () => location.reload();
evtSource.onerror = () => console.warn('Live reload connection lost.');
</script>
"""


def scan_files():
    state = {}
    for root, _, files in os.walk(ROOT):
        for filename in files:
            path = Path(root) / filename
            if path.suffix.lower() in WATCH_EXTENSIONS:
                try:
                    state[str(path)] = path.stat().st_mtime
                except OSError:
                    continue
    return state


def watch_changes(poll_interval=1.0):
    old_state = scan_files()
    while True:
        time.sleep(poll_interval)
        new_state = scan_files()
        if new_state != old_state:
            with CLIENTS_LOCK:
                for wfile in CLIENTS[:]:
                    try:
                        wfile.write(b"data: reload\n\n")
                        wfile.flush()
                    except Exception:
                        CLIENTS.remove(wfile)
            old_state = new_state


class ReloadHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = urllib.parse.urlparse(path).path
        if path == "/":
            path = "/index.html"
        path = path.lstrip("/")
        full_path = ROOT / path
        return str(full_path)

    def do_GET(self):
        if self.path == RELOAD_PATH:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            with CLIENTS_LOCK:
                CLIENTS.append(self.wfile)
            try:
                while True:
                    time.sleep(10)
            except BrokenPipeError:
                pass
            return

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")

        if os.path.exists(path) and path.endswith(".html"):
            try:
                with open(path, "rb") as f:
                    content = f.read()
                if b"</body>" in content.lower():
                    lower = content.lower()
                    idx = lower.rfind(b"</body>")
                    content = content[:idx] + INJECT_SCRIPT + content[idx:]
                else:
                    content += INJECT_SCRIPT
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
                return
            except OSError:
                self.send_error(404, "File not found")
                return

        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


if __name__ == "__main__":
    watcher = threading.Thread(target=watch_changes, daemon=True)
    watcher.start()
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), ReloadHTTPRequestHandler) as httpd:
        print(f"Serving {ROOT} at http://127.0.0.1:{PORT}")
        print("Open that URL in your browser; edits to .html/.css/.js will auto-reload.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down server.")
