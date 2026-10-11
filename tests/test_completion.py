"""Bash completion tests for ctx."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPLETION = ROOT / "src" / "ctx-completion.bash"


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = self.root / "cfg" / "ctx"
        (self.cfg / "projects").mkdir(parents=True)
        (self.cfg / "archived").mkdir(parents=True)
        for slug in ("mm", "school", "work"):
            (self.cfg / "projects" / f"{slug}.conf").write_text(f"name={slug}\\n")
        (self.cfg / "archived" / "old.conf").write_text("name=old\\n")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        plugin = self.bin / "ctx-ext-hello"
        plugin.write_text("#!/usr/bin/env bash\\nexit 0\\n")
        plugin.chmod(0o755)
        self.env = dict(
            os.environ,
            XDG_CONFIG_HOME=str(self.root / "cfg"),
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
        )

    def complete(self, *words):
        quoted = " ".join(repr(w) for w in words)
        script = (
            f"source {COMPLETION!s}\\n"
            f"COMP_WORDS=({quoted})\\n"
            "COMP_CWORD=$((${#COMP_WORDS[@]} - 1))\\n"
            "_ctx_completion\\n"
            "printf '%s\\\\n' \"${COMPREPLY[@]}\"\\n"
        )
        result = subprocess.run(
            ["bash", "-c", script],
            env=self.env, capture_output=True, text=True, timeout=5, check=True,
        )
        return result.stdout.splitlines()

    def test_top_level_includes_shorthand_and_extensions(self):
        values = self.complete("ctx", "")
        self.assertIn("s", values)
        self.assertIn("a", values)
        self.assertIn("hello", values)

    def test_switch_completes_active_contexts(self):
        values = self.complete("ctx", "s", "")
        self.assertIn("mm", values)
        self.assertIn("school", values)
        self.assertNotIn("old", values)

    def test_archive_and_unarchive_use_correct_context_sets(self):
        self.assertIn("mm", self.complete("ctx", "arc", ""))
        values = self.complete("ctx", "unarc", "")
        self.assertEqual(values, ["old"])

    def test_agent_namespace_completes_short_actions(self):
        values = self.complete("ctx", "a", "")
        for action in ("p", "g", "d", "a", "x"):
            self.assertIn(action, values)


if __name__ == "__main__":
    unittest.main()
