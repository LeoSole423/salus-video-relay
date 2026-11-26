"""Controls only the three RTSP publishers feeding the NVR relay."""
import hmac
import json
import os
import re
import signal
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PATHS = ("salus", "salus-ptz", "salus-trasera")
SOURCES = dict(zip(PATHS, (
    os.environ["ROVER_RTSP_URL"],
    os.environ["ROVER_PTZ_RTSP_URL"],
    os.environ["ROVER_REAR_RTSP_URL"],
)))
TOKEN = os.environ["NVR_CONTROL_TOKEN"]
PUBLISH_PASSWORD = os.environ["NVR_PUBLISH_PASSWORD"]
if not all(re.fullmatch(r"[A-Za-z0-9_-]{32,128}", value) for value in (TOKEN, PUBLISH_PASSWORD)):
    raise SystemExit("Use distinct random tokens of at least 32 URL-safe characters")
if TOKEN == PUBLISH_PASSWORD:
    raise SystemExit("Use distinct control and publishing credentials")


class Relay:
    def __init__(self):
        self.enabled = False
        self.children = {}
        self.last_frame = {}
        self.retry_at = {}

    def update(self):
        for path, source in SOURCES.items():
            child = self.children.get(path)
            now = time.monotonic()
            if child is not None:
                if child.poll() is None:
                    progress = child.stdout.read() or b""
                    if re.search(rb"frame=[1-9][0-9]*", progress):
                        self.last_frame[path] = now
                    continue
                child.stdout.close()
                del self.children[path]
                self.last_frame.pop(path, None)
                self.retry_at[path] = now + 3
            if self.enabled and now >= self.retry_at.get(path, 0):
                target = f"rtsp://relay_publisher:{PUBLISH_PASSWORD}@mediamtx:8554/{path}"
                child = subprocess.Popen([
                    "ffmpeg", "-nostdin", "-loglevel", "quiet", "-stats_period", "1",
                    "-progress", "pipe:1", "-rtsp_transport", "tcp", "-timeout", "5000000",
                    "-i", source, "-map", "0:v:0", "-c:v", "copy",
                    "-f", "rtsp", "-rtsp_transport", "tcp", target,
                ], stdout=subprocess.PIPE)
                os.set_blocking(child.stdout.fileno(), False)
                self.children[path] = child

    def pause(self):
        self.enabled = False
        for child in self.children.values():
            if child.poll() is None:
                child.terminate()
        for child in self.children.values():
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            child.stdout.close()
        self.children.clear()
        self.last_frame.clear()
        self.retry_at.clear()

    def state(self):
        return {
            "enabled": self.enabled,
            "online": sum(time.monotonic() - stamp < 5 for stamp in self.last_frame.values()),
        }


relay = Relay()


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def authorized(self):
        supplied = self.headers.get("Authorization", "").encode()
        if not hmac.compare_digest(supplied, f"Bearer {TOKEN}".encode()):
            self.reply(401, {})
            return False
        if self.path != "/transmission":
            self.reply(404, {})
            return False
        return True

    def do_GET(self):
        if self.authorized():
            relay.update()
            self.reply(200, relay.state())

    def do_PUT(self):
        if not self.authorized():
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 128:
                raise ValueError
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict) or type(body.get("enabled")) is not bool:
                raise ValueError
        except (ValueError, OSError):
            self.reply(400, {})
            return
        if body["enabled"]:
            relay.enabled = True
            relay.update()
        else:
            relay.pause()
        self.reply(200, relay.state())


class ControlServer(HTTPServer):
    timeout = 0.5

    def get_request(self):
        conn, addr = super().get_request()
        conn.settimeout(3)
        return conn, addr


running = True


def stop(_signum, _frame):
    global running
    running = False


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    with ControlServer(("0.0.0.0", 8090), Handler) as server:
        while running:
            relay.update()
            server.handle_request()
finally:
    relay.pause()
