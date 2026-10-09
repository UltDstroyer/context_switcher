"""Extension contract tests using fake executable add-ons; no AI install needed."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

CTX = Path(__file__).resolve().parents[1] / "src" / "ctx"


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "cfg" / "ctx"
        (self.config / "projects").mkdir(parents=True)
        (self.config / "state").mkdir(parents=True)
        (self.config / "projects" / "research.conf").write_text("name=Research\n")
        (self.config / "state" / "current").write_text("research\n")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "dispatch"
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.root / "cfg"),
                        EXT_LOG=str(self.log),
                        PATH=str(self.bin) + os.pathsep + os.environ["PATH"])
        self.plugin("agent")
        self.plugin("hello")

    def plugin(self, name):
        script = self.bin / ("ctx-ext-" + name)
        script.write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            'printf "%s\\n" "$CTX_EXTENSION_API_VERSION" "$CTX_CONTEXT" '
            '"$CTX_CONFIG_ROOT" "$@" > "$EXT_LOG"\n'
        )
        script.chmod(0o755)

    def ctx(self, *args, success=True):
        result = subprocess.run(["bash", str(CTX), *args],
                                env=self.env, capture_output=True, text=True,
                                timeout=6)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def observed(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_any_extension_dispatches_without_core_changes(self):
        self.ctx("hello", "say", "two words")
        self.assertEqual(self.observed(), ["1", "research", str(self.config),
                                           "say", "two words"])

    def test_agent_is_an_ordinary_extension(self):
        self.ctx("agent", "mode", "quiet")
        self.assertEqual(self.observed(), ["1", "research", str(self.config),
                                           "mode", "quiet"])

    def test_extension_works_without_context(self):
        (self.config / "state" / "current").unlink()
        self.ctx("hello", "ping")
        self.assertEqual(self.observed(), ["1", "", str(self.config), "ping"])

    def test_extensions_lists_installed_executables(self):
        result = self.ctx("extensions")
        self.assertEqual(result.stdout.splitlines(), ["agent", "hello"])

    def test_extension_missing_is_clear(self):
        result = self.ctx("absent", "hello", success=False)
        self.assertIn("not installed", result.stderr)

    def test_invalid_extension_names_are_rejected(self):
        for name in ("../agent", "UPPER", "a.b", "_hidden"):
            with self.subTest(name=name):
                self.ctx(name, success=False)

    def test_invalid_context_does_not_reach_extension(self):
        (self.config / "state" / "current").write_text("../research")
        result = self.ctx("hello", success=False)
        self.assertIn("invalid context slug", result.stderr)
        self.assertFalse(self.log.exists())

    def test_missing_context_config_does_not_reach_extension(self):
        (self.config / "state" / "current").write_text("nope")
        self.ctx("hello", success=False)
        self.assertFalse(self.log.exists())

    def test_agent_not_required_for_core_help(self):
        (self.bin / "ctx-ext-agent").unlink()
        self.assertIn("ctx extensions", self.ctx("--help").stdout)

    def test_agent_not_required_for_core_current(self):
        (self.bin / "ctx-ext-agent").unlink()
        self.assertEqual(self.ctx("current").stdout.strip(), "research")

    def test_no_automatic_extension_execution(self):
        self.ctx("current")
        self.ctx("extensions")
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
