#!/usr/bin/env python3
"""Static frontend server with a tiny local API proxy for backend development."""
from __future__ import annotations

import argparse
import json
from http.client import HTTPConnection
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]


class DevProxyHandler(SimpleHTTPRequestHandler):
    market_host = "127.0.0.1"
    market_port = 5001
    news_host = "127.0.0.1"
    news_port = 5000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/market/"):
            self.proxy_to(self.market_host, self.market_port)
            return
        if self.path.startswith("/api/news/"):
            self.proxy_to(self.news_host, self.news_port)
            return
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/market/"):
            self.proxy_to(self.market_host, self.market_port)
            return
        if self.path.startswith("/api/news/"):
            self.proxy_to(self.news_host, self.news_port)
            return
        self.send_json(404, {"message": "proxy route not found"})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def end_headers(self):
        self.send_cors_headers()
        super().end_headers()

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def proxy_to(self, host: str, port: int):
        body = None
        if self.command in {"POST", "PUT", "PATCH"}:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else None

        headers = {
            "Content-Type": self.headers.get("Content-Type", "application/json"),
            "Accept": self.headers.get("Accept", "application/json"),
        }
        target = urlsplit(self.path)
        path = target.path + (f"?{target.query}" if target.query else "")

        try:
            conn = HTTPConnection(host, port, timeout=60)
            conn.request(self.command, path, body=body, headers=headers)
            response = conn.getresponse()
            payload = response.read()
        except OSError as error:
            self.send_json(502, {"message": f"backend unavailable: {error}"})
            return
        finally:
            try:
                conn.close()
            except UnboundLocalError:
                pass

        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in {"connection", "transfer-encoding", "content-length"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--market-port", type=int, default=5001)
    parser.add_argument("--news-port", type=int, default=5000)
    args = parser.parse_args()

    DevProxyHandler.market_port = args.market_port
    DevProxyHandler.news_port = args.news_port

    server = ThreadingHTTPServer((args.host, args.port), DevProxyHandler)
    print(f"Frontend: http://{args.host}:{args.port}")
    print(f"Proxy: /api/market -> http://127.0.0.1:{args.market_port}")
    print(f"Proxy: /api/news -> http://127.0.0.1:{args.news_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
