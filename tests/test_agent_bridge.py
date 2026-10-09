"""Verify the ctx -> ctx-agent CLI boundary without an installed AI service."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

CTX = Path(__file__).resolve().parents[1] / "src" / "ctx"


class AgentBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "cfg" / "ctx"
        (self.config / "projects").mkdir(parents=True)
        (self.config / "state").mkdir(parents=True)
        for slug in ("research", "gaming"):
            (self.config / "projects" / (slug + ".conf")).write_text("name=" + slug + "\n")
        (self.config / "state" / "current").write_text("research\n")
        bindir = self.root / "bin"
        bindir.mkdir()
        self.log = self.root / "agent-argv"
        self.env = dict(
            os.environ,
            XDG_CONFIG_HOME=str(self.root / "cfg"),
            AGENT_ARGV_LOG=str(self.log),
            PATH=str(bindir) + os.pathsep + os.environ["PATH"],
        )
        for name in ("ctx-agent", "ctx-agent-media"):
            path = bindir / name
            path.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'printf "%s\\n" "$@" > "$AGENT_ARGV_LOG"\n'
            )
            path.chmod(0o755)

    def run_ctx(self, *args, ok=True):
        proc = subprocess.run(
            ["bash", str(CTX), *args], capture_output=True, text=True,
            env=self.env, timeout=6,
        )
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stderr)
        else:
            self.assertNotEqual(proc.returncode, 0)
        return proc

    def argv(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_uses_active_context_for_submit(self):
        self.run_ctx("agent", "submit", "fix navigation")
        self.assertEqual(self.argv(), ["submit", "research", "fix navigation"])

    def test_project_override_does_not_require_ctx_context(self):
        (self.config / "state" / "current").unlink()
        self.run_ctx("agent", "submit", "--project", "outside_1", "run tests")
        self.assertEqual(self.argv(), ["submit", "outside_1", "run tests"])

    def test_no_context_requires_explicit_project(self):
        (self.config / "state" / "current").unlink()
        result = self.run_ctx("agent", "submit", "run tests", ok=False)
        self.assertIn("no active context", result.stderr)
        self.assertFalse(self.log.exists())

    def test_project_scoped_commands(self):
        self.run_ctx("agent", "init")
        self.assertEqual(self.argv(), ["init", "research"])
        self.run_ctx("agent", "notes")
        self.assertEqual(self.argv(), ["notes", "research"])
        self.run_ctx("agent", "note", "branch", "main")
        self.assertEqual(self.argv(), ["note", "research", "branch", "main"])

    def test_import_preserves_spaces_and_explicit_project(self):
        self.run_ctx("agent", "import", "--project", "demo", "/home/me/My Sources")
        self.assertEqual(self.argv(), ["import", "demo", "/home/me/My Sources"])

    def test_resource_mode_forwarded_without_context(self):
        (self.config / "state" / "current").unlink()
        self.run_ctx("agent", "mode", "quiet")
        self.assertEqual(self.argv(), ["mode", "quiet"])

    def test_status_and_logs_aliases(self):
        self.run_ctx("agent", "status")
        self.assertEqual(self.argv(), ["health"])
        self.run_ctx("agent", "status", "123abc")
        self.assertEqual(self.argv(), ["show", "123abc"])
        self.run_ctx("agent", "logs", "123abc")
        self.assertEqual(self.argv(), ["events", "123abc"])

    def test_review_and_apply_must_be_explicit(self):
        self.run_ctx("agent", "diff", "123abc")
        self.assertEqual(self.argv(), ["diff", "123abc"])
        self.run_ctx("agent", "apply", "123abc")
        self.assertEqual(self.argv(), ["apply", "123abc"])

    def test_media_bridge_is_explicit_user_command(self):
        self.run_ctx("agent", "media", "record", "start")
        self.assertEqual(self.argv(), ["record", "start"])
        self.run_ctx("agent", "media", "narrate", "Hello world", "/tmp/voice.wav")
        self.assertEqual(self.argv(), ["narrate", "Hello world", "/tmp/voice.wav"])

    def test_unknown_agent_command_is_rejected(self):
        result = self.run_ctx("agent", "run-host-shell", ok=False)
        self.assertIn("unknown agent command", result.stderr)
        self.assertFalse(self.log.exists())

    def test_agent_help_does_not_require_backend(self):
        (self.root / "bin" / "ctx-agent").unlink()
        result = self.run_ctx("agent", "help")
        self.assertIn("ctx agent submit", result.stdout)

    def test_agent_command_does_not_start_monitoring(self):
        self.run_ctx("agent", "health")
        self.assertEqual(self.argv(), ["health"])
        self.assertFalse((self.config / "state" / "monitoring").exists())


if __name__ == "__main__":
    unittest.main()
