#!/usr/bin/env python3
"""Minimal OpenAI-compatible /v1/chat/completions mock for integration tests.

Listens on 127.0.0.1 on an auto-chosen port and returns a canned response.
The first line of stdout is the bound port — callers parse that to reach
the server.

Env:
    MOCK_DECISION  — "allow" | "deny" | "blocked_pending_approval" (default "deny")
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


DECISION = os.environ.get("MOCK_DECISION", "deny")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        body = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({"decision": DECISION}),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *args, **kwargs):
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 0), Handler)
    # Report the bound port to the caller before serving.
    print(server.server_address[1], flush=True)
    server.serve_forever()
