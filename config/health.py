"""Lightweight health check and readiness server for Docker container and local runtime.

Serves /health and / readiness endpoints using standard library http.server,
providing zero-dependency container health probing and startup verification.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from config.system_config import get_config


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP Request handler for container health and readiness probes."""

    def log_message(self, format: str, *args: object) -> None:
        """Suppress default access logging to keep stdout clean."""
        pass

    def do_GET(self) -> None:
        cfg = get_config()
        if self.path in ("/health", "/healthz", "/"):
            payload = {
                "status": "ok",
                "service": "pii-masking",
                "system_version": cfg.system_version,
                "api_version": cfg.api_version,
                "environment": cfg.app_env,
            }
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')


def run_health_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run lightweight HTTP server for health checking."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    print(f"Health server running on http://{host}:{port}/health (PID {os.getpid()})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down health server...")
        httpd.server_close()


if __name__ == "__main__":
    port_str = os.environ.get("APP_PORT", "8000")
    run_health_server(port=int(port_str))
