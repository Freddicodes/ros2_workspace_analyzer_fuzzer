#!/usr/bin/env python3
"""
ROS2 Communication Graph - Live WebSocket Server
=================================================
Streams graph data to the browser visualization in real time.

Install dependencies:
    pip install websockets

Run:
    python server.py                        # serves on ws://localhost:8765
    python server.py --port 9000            # custom port
    python server.py --file graph.json      # push a file on startup
    python server.py --watch graph.json     # auto-push when file changes

Then open ros2_graph.html and click "Connect".

Sending data programmatically
------------------------------
You can push graph updates via HTTP POST from any process:

    curl -X POST http://localhost:8766/push \\
         -H "Content-Type: application/json" \\
         -d @communication.json

The server accepts the raw ROS2 topic→{publisher,subscriber} format
OR a pre-parsed {"nodes":[…], "edges":[…], "topic_details":{…}} dict.
"""

import argparse
import asyncio
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

try:
    import websockets
    from websockets.asyncio.server import serve
except ImportError:
    print("ERROR: websockets not installed.\n  pip install websockets")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("ros2-graph-server")

# ── Shared state ──────────────────────────────────────────────────────────────
_clients: set = set()
_latest_payload: str | None = None  # last-pushed JSON string
_loop: asyncio.AbstractEventLoop | None = None

# ── WebSocket server ──────────────────────────────────────────────────────────


async def ws_handler(websocket):
    """Handle a single WebSocket client connection."""
    _clients.add(websocket)
    remote = websocket.remote_address
    log.info(f"Client connected   {remote}  (total: {len(_clients)})")

    # Send current graph immediately on connect
    if _latest_payload is not None:
        try:
            await websocket.send(_latest_payload)
            log.info(f"Sent current graph to {remote}")
        except Exception as e:
            log.warning(f"Failed to send initial payload: {e}")

    try:
        async for message in websocket:
            # Clients can also push data back (optional)
            try:
                _ = json.loads(message)
                log.info(f"Received data from client {remote}, broadcasting…")
                await _broadcast(message)
            except json.JSONDecodeError:
                log.warning(f"Non-JSON message from {remote}: {message[:80]}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        _clients.discard(websocket)
        log.info(f"Client disconnected {remote}  (total: {len(_clients)})")


async def _broadcast(payload: str):
    """Send payload to all connected clients."""
    global _latest_payload
    _latest_payload = payload
    if not _clients:
        return
    results = await asyncio.gather(*[c.send(payload) for c in list(_clients)], return_exceptions=True)
    ok = sum(1 for r in results if not isinstance(r, Exception))
    log.info(f"Broadcast → {ok}/{len(_clients)} clients")


# ── HTTP push endpoint ────────────────────────────────────────────────────────


class PushHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server that accepts POST /push to inject new graph data."""

    def log_message(self, format, *args):
        log.debug("HTTP " + format % args)

    def do_GET(self):
        if self.path in ("/", "/index.html", "/ros2_graph.html"):
            # Serve the visualization HTML from the same directory as the server
            html_candidates = [
                Path(__file__).parent / "ros2_graph.html",
                Path(__file__).parent / "ros2_graph (1).html",
            ]
            for p in html_candidates:
                if p.exists():
                    body = p.read_bytes()
                    self._respond(200, body, "text/html; charset=utf-8")
                    return
            self._respond(404, b"ros2_graph.html not found next to server.py")
        elif self.path == "/data":
            if _latest_payload is None:
                self._respond(204, b"")
                return
            self._respond(200, _latest_payload.encode("utf-8"), "application/json")
        elif self.path == "/status":
            body = json.dumps({"clients": len(_clients), "has_data": _latest_payload is not None}).encode()
            self._respond(200, body, "application/json")
        else:
            self._respond(200, b"ROS2 Graph Server running", "text/plain")

    def do_POST(self):
        if self.path not in ("/push", "/data"):
            self._respond(404, b"Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            json.loads(raw)  # validate JSON
        except json.JSONDecodeError as e:
            self._respond(400, f"Invalid JSON: {e}".encode())
            return

        # Schedule broadcast on the asyncio loop
        if _loop:
            asyncio.run_coroutine_threadsafe(_broadcast(raw.decode()), _loop)
            self._respond(200, b'{"ok":true}', "application/json")
            log.info(f"HTTP POST /push  {len(raw)} bytes  from {self.client_address[0]}")
        else:
            self._respond(503, b"Server not ready yet")

    def _respond(self, code, body=b"", ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def start_http_server(port: int):
    server = HTTPServer(("0.0.0.0", port), PushHandler)
    log.info(f"HTTP push endpoint  http://localhost:{port}/push")
    server.serve_forever()


# ── File watcher ──────────────────────────────────────────────────────────────


async def watch_file(path: Path, interval: float = 1.0):
    """Poll a file for changes and broadcast when it updates."""
    last_mtime = None
    log.info(f"Watching {path} for changes…")
    while True:
        try:
            mtime = path.stat().st_mtime
            if mtime != last_mtime:
                last_mtime = mtime
                data = path.read_text(encoding="utf-8")
                json.loads(data)  # validate
                await _broadcast(data)
                log.info(f"File changed, broadcast {len(data)} bytes")
        except FileNotFoundError:
            log.warning(f"Watched file not found: {path}")
        except json.JSONDecodeError as e:
            log.warning(f"File is not valid JSON: {e}")
        except Exception as e:
            log.error(f"Watch error: {e}")
        await asyncio.sleep(interval)


# ── Example: generate dummy graph data ───────────────────────────────────────


def make_example_payload() -> str:
    """
    Generate a tiny example in the raw ROS2 format so you can test
    the server without a real graph file.
    """
    example = {
        "/example/cmd": {
            "publisher": [
                {
                    "name": "publisher_node",
                    "path": "/nodes/publisher_node.py",
                    "subscriptions": [],
                    "publishers": [{"msg_type": "String", "topic": "/example/cmd", "qos_service_profile": "10"}],
                }
            ],
            "subscriber": [
                {
                    "name": "subscriber_node",
                    "path": "/nodes/subscriber_node.py",
                    "subscriptions": [
                        {
                            "msg_type": "String",
                            "topic": "/example/cmd",
                            "callback": "self.on_cmd",
                            "qos_service_profile": "10",
                        }
                    ],
                    "publishers": [],
                }
            ],
        },
        "/example/status": {
            "publisher": [
                {
                    "name": "subscriber_node",
                    "path": "/nodes/subscriber_node.py",
                    "subscriptions": [],
                    "publishers": [{"msg_type": "Bool", "topic": "/example/status", "qos_service_profile": "10"}],
                }
            ],
            "subscriber": [],
        },
    }
    return json.dumps(example)


# ── Main ──────────────────────────────────────────────────────────────────────


async def main(args):
    global _loop, _latest_payload
    _loop = asyncio.get_running_loop()

    # Load initial file if given
    if args.file:
        p = Path(args.file)
        if p.exists():
            try:
                _latest_payload = p.read_text(encoding="utf-8")
                json.loads(_latest_payload)  # validate
                log.info(f"Loaded initial graph from {p}  ({len(_latest_payload)} bytes)")
            except Exception as e:
                log.error(f"Could not load {p}: {e}")
                _latest_payload = None
        else:
            log.warning(f"File not found: {p}")
    elif args.example:
        _latest_payload = make_example_payload()
        log.info("Using built-in example graph")

    # Start HTTP push server in background thread
    http_thread = Thread(target=start_http_server, args=(args.http_port,), daemon=True)
    http_thread.start()

    # Start file watcher if requested
    if args.watch:
        asyncio.create_task(watch_file(Path(args.watch), interval=args.watch_interval))

    # Start WebSocket server
    log.info(f"WebSocket server    ws://localhost:{args.port}")
    log.info(f"Open in browser:    http://localhost:{args.http_port}")
    log.info("  (or open ros2_graph.html directly — it is now fully self-contained)")
    log.info("-" * 50)

    async with serve(ws_handler, "0.0.0.0", args.port):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ROS2 graph WebSocket server", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__
    )
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument("--http-port", type=int, default=8766, help="HTTP push port (default: 8766)")
    parser.add_argument("--file", type=str, default=None, help="JSON file to push on startup")
    parser.add_argument("--watch", type=str, default=None, help="JSON file to watch and auto-push on change")
    parser.add_argument(
        "--watch-interval", type=float, default=1.0, help="Watch poll interval in seconds (default: 1.0)"
    )
    parser.add_argument("--example", action="store_true", help="Push a built-in example graph on startup")
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        log.info("Server stopped")
