#!/usr/bin/env python3
"""Static file server with clean URL rewriting for Daily Market Sense."""

import http.server
import socketserver
import os

PORT = 3000
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


class RewriteHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUT_DIR, **kwargs)

    def translate_path(self, path):
        """Override to support clean URLs (no .html extension)."""
        p = path.split("?")[0].split("#")[0]
        if p == "/":
            path = "/index.html"
        elif not os.path.splitext(p)[1]:
            test_path = p.rstrip("/") + ".html"
            fs_test = OUT_DIR + test_path.replace("/", os.sep)
            if os.path.exists(fs_test):
                path = test_path
        return super().translate_path(path)

    def log_message(self, format, *args):
        pass


# Support .webmanifest
RewriteHandler.extensions_map[".webmanifest"] = "application/manifest+json"


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), RewriteHandler) as httpd:
        print(f"[server] http://localhost:{PORT}")
        print(f"[server] Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("[server] Stopped")
