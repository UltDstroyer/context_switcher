"""Black-box tests for ctxd guarded updates and context isolation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DAEMON = ROOT / "src" / "ctxd"


@unittest.skipUnless(shutil.which("jq") and shutil.which("flock"), "jq and flock required")
class GuardedUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = os.environ.copy()
        self.env["XDG_CONFIG_HOME"] = self.tmp.name
        self.env["XDG_RUNTIME_DIR"] = self.tmp.name

    def command(self, value):
        process = subprocess.run(
            ["bash", str(DAEMON), "--handle-client"],
            input=value + "\n", text=True, capture_output=True,
            env=self.env, timeout=5, check=True
        )
        return process.stdout.strip()

    def test_rejects_old_context_after_switch(self):
        self.assertEqual(self.command("START\tresearch"), "OK")
        self.assertEqual(
            self.command('UPDATE_CTX\tresearch\tfirefox\t{"marker":"A"}'), "OK")
        self.assertEqual(self.command("START\tprogramming"), "OK")
        self.assertEqual(
            self.command('UPDATE_CTX\tresearch\tfirefox\t{"marker":"A-stale"}'),
            "IGNORED")
        self.assertEqual(
            self.command('UPDATE_CTX\tprogramming\tfirefox\t{"marker":"B"}'), "OK")
        self.assertEqual(self.command("CHECKPOINT\tprogramming"), "OK")
        snapshot = Path(self.tmp.name, "ctx", "state", "programming", "snapshot.json")
        state = json.loads(snapshot.read_text())
        self.assertEqual(state["live_updates"]["firefox"]["marker"], "B")

    def test_no_monitoring_drops_updates(self):
        self.assertEqual(
            self.command('UPDATE_CTX\tresearch\tfirefox\t{"marker":"A"}'),
            "IGNORED")
        self.assertEqual(self.command("START\tresearch"), "OK")
        self.assertEqual(self.command("STOP"), "OK")
        self.assertEqual(
            self.command('UPDATE_CTX\tresearch\tfirefox\t{"marker":"A"}'),
            "IGNORED")

    def test_bad_json_rejected(self):
        self.assertEqual(self.command("START\tresearch"), "OK")
        self.assertEqual(
            self.command("UPDATE_CTX\tresearch\tfirefox\t{invalid"),
            "ERR invalid json")


if __name__ == "__main__":
    unittest.main()
