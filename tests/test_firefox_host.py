"""Contract tests for the Firefox native messaging bridge (no Firefox required)."""
import importlib.util
import json
from pathlib import Path
import struct
import unittest

HOST = Path(__file__).resolve().parents[1] / "native-host" / "firefox_host.py"
spec = importlib.util.spec_from_file_location("firefox_host", HOST)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


def sample_snapshot():
    return {
        "schema_version": 1,
        "adapter": "firefox",
        "captured_at": "2026-10-09T10:00:00.000Z",
        "windows": [{
            "id": 12,
            "focused": True,
            "tabs": [{
                "id": 21, "index": 0,
                "url": "https://example.org/research",
                "title": "Research",
                "active": True, "pinned": False,
                "highlighted": False, "muted": False,
                "discarded": False,
                "cookie_store_id": "firefox-default"
            }]
        }]
    }


class NativeMessageTests(unittest.TestCase):
    def test_partial_native_frames(self):
        packet = host.encode_message({"type": "status"})
        buf = bytearray(packet[:5])
        self.assertEqual(host.extract_messages(buf), [])
        buf.extend(packet[5:])
        self.assertEqual(host.extract_messages(buf), [{"type": "status"}])
        self.assertEqual(buf, bytearray())

    def test_reject_huge_frame(self):
        buf = bytearray(struct.pack("<I", host.MAX_MESSAGE_BYTES + 1))
        with self.assertRaises(ValueError):
            host.extract_messages(buf)

    def test_status_values(self):
        self.assertEqual(host.parse_status("monitoring\tresearch")["context"], "research")
        self.assertIsNone(host.parse_status("stopped")["context"])
        self.assertFalse(host.parse_status("oops")["connected"])
        self.assertFalse(host.parse_status("monitoring\t../../bad")["connected"])

    def test_snapshot_is_context_bound(self):
        calls = []

        def daemon(command):
            calls.append(command)
            return "OK"

        result = host.handle_message({
            "type": "snapshot",
            "context": "research",
            "snapshot": sample_snapshot()
        }, daemon)
        self.assertEqual(result, {"type": "ack", "accepted": True})
        self.assertTrue(calls[0].startswith("UPDATE_CTX\tresearch\tfirefox\t"))
        payload = json.loads(calls[0].split("\t", 3)[3])
        self.assertEqual(payload["windows"][0]["tabs"][0]["url"], "https://example.org/research")

    def test_rejection_is_reported(self):
        message = {"type": "snapshot", "context": "research", "snapshot": sample_snapshot()}
        self.assertEqual(host.handle_message(message, lambda _: "IGNORED"),
                         {"type": "ack", "accepted": False})

    def test_private_window_is_rejected(self):
        snapshot = sample_snapshot()
        snapshot["windows"][0]["incognito"] = True
        result = host.handle_message(
            {"type": "snapshot", "context": "research", "snapshot": snapshot},
            lambda _: self.fail("Should not contact daemon"))
        self.assertEqual(result["type"], "error")

    def test_unknown_context_rejected_without_update(self):
        result = host.handle_message(
            {"type": "snapshot", "context": "../other", "snapshot": sample_snapshot()},
            lambda _: self.fail("Should not contact daemon"))
        self.assertEqual(result["type"], "error")

    def test_cannot_capture_arbitrary_page_content(self):
        snapshot = sample_snapshot()
        snapshot["windows"][0]["tabs"][0]["title"] = 42
        self.assertFalse(host.check_snapshot(snapshot))


if __name__ == "__main__":
    unittest.main()
