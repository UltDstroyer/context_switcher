#!/usr/bin/env python3
"""Firefox native-messaging bridge for the local ctxd Unix socket.

Protocol: Firefox native messaging uses 32-bit little-endian length-prefixed JSON.
The host never opens a listening port and never contacts an external service.
"""
import json
import os
import re
import selectors
import socket
import struct
import sys

HOST_NAME = "org.ctx_switcher.firefox"
MAX_MESSAGE_BYTES = 8 * 1024 * 1024
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def daemon_request(line):
    """Send a single line to ctxd. One connection per command."""
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or "/tmp/ctx-" + str(os.getuid())
    path = os.path.join(runtime_dir, "ctxd.sock")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(2)
        conn.connect(path)
        conn.sendall((line + "\n").encode("utf-8"))
        reply = bytearray()
        while b"\n" not in reply:
            chunk = conn.recv(4096)
            if not chunk or len(reply) > 65536:
                break
            reply.extend(chunk)
    return reply.decode("utf-8").split("\n", 1)[0]


def parse_status(reply):
    if reply == "stopped":
        return {"type": "status", "connected": True, "context": None}
    if reply.startswith("monitoring\t"):
        context = reply.partition("\t")[2]
        if SLUG.fullmatch(context):
            return {"type": "status", "connected": True, "context": context}
    return {"type": "status", "connected": False, "context": None}


def get_status(request=daemon_request):
    try:
        return parse_status(request("STATUS"))
    except (OSError, UnicodeError):
        return {"type": "status", "connected": False, "context": None}


def check_snapshot(snapshot):
    """Reject unexpected content rather than forwarding arbitrary objects to ctxd."""
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
        return False
    if snapshot.get("adapter") != "firefox":
        return False
    windows = snapshot.get("windows")
    if not isinstance(windows, list) or len(windows) > 128:
        return False
    total_tabs = 0
    for window in windows:
        if not isinstance(window, dict) or window.get("incognito"):
            return False
        tabs = window.get("tabs")
        if not isinstance(tabs, list):
            return False
        total_tabs += len(tabs)
        if total_tabs > 5000:
            return False
        for tab in tabs:
            if not isinstance(tab, dict) or tab.get("incognito"):
                return False
            url = tab.get("url")
            title = tab.get("title")
            if url is not None and (not isinstance(url, str) or len(url) > 32768):
                return False
            if not isinstance(title, str) or len(title) > 8192:
                return False
    return True


def handle_message(message, request=daemon_request):
    if not isinstance(message, dict):
        return {"type": "error", "message": "Expected an object"}
    if message.get("type") == "status":
        return get_status(request)
    if message.get("type") != "snapshot":
        return {"type": "error", "message": "Unknown message type"}
    context = message.get("context")
    snapshot = message.get("snapshot")
    if not isinstance(context, str) or not SLUG.fullmatch(context):
        return {"type": "error", "message": "Invalid context"}
    if not check_snapshot(snapshot):
        return {"type": "error", "message": "Invalid Firefox snapshot"}
    data = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    if len(data.encode("utf-8")) > MAX_MESSAGE_BYTES:
        return {"type": "error", "message": "Snapshot too large"}
    try:
        response = request("UPDATE_CTX\t" + context + "\tfirefox\t" + data)
    except OSError:
        return {"type": "ack", "accepted": False}
    return {"type": "ack", "accepted": response == "OK"}


def encode_message(message):
    payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
    return struct.pack("<I", len(payload)) + payload


def extract_messages(buffer):
    """Read complete Firefox native-message frames; retain partial frames."""
    messages = []
    while len(buffer) >= 4:
        size = struct.unpack("<I", buffer[:4])[0]
        if size > MAX_MESSAGE_BYTES:
            raise ValueError("Native message exceeds size limit")
        if len(buffer) < 4 + size:
            break
        payload = bytes(buffer[4:4 + size])
        del buffer[:4 + size]
        messages.append(json.loads(payload.decode("utf-8")))
    return messages


def main():
    fd = sys.stdin.fileno()
    selector = selectors.DefaultSelector()
    selector.register(fd, selectors.EVENT_READ)
    pending = bytearray()
    previous_status = None

    def reply(message):
        sys.stdout.buffer.write(encode_message(message))
        sys.stdout.buffer.flush()

    while True:
        ready = selector.select(timeout=1.0)
        if ready:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            pending.extend(chunk)
            if len(pending) > MAX_MESSAGE_BYTES + 4:
                break
            try:
                messages = extract_messages(pending)
            except (UnicodeError, ValueError, json.JSONDecodeError):
                break
            for message in messages:
                result = handle_message(message)
                reply(result)
                if result["type"] == "status":
                    previous_status = result

        # The port is long-lived. Announce ctx switch/exit even when tabs don't change.
        status = get_status()
        if status != previous_status:
            reply(status)
            previous_status = status


if __name__ == "__main__":
    main()
