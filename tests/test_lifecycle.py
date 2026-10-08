"""Exercise lifecycle ordering and failures without starting real services."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


CLI = Path(__file__).resolve().parents[1] / "src" / "ctx"


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config" / "ctx"
        self.log = self.root / "events"
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.root / "config"),
                        PATH=f"{bin_dir}:{os.environ['PATH']}",
                        TEST_LOG=str(self.log), TEST_ROOT=str(self.root))
        self.script(bin_dir / "ctxdctl", '''
if [[ "$1" == ping ]]; then exit 0; fi
printf '%s %s\n' "$1" "${2:-}" >> "$TEST_LOG"
[[ ! -f "$TEST_ROOT/fail-$1" ]]
''')
        self.script(bin_dir / "systemctl", '''
printf '%s\n' "$*" >> "$TEST_LOG"
[[ ! -f "$TEST_ROOT/fail-$2" ]]
''')
        projects = self.config / "projects"
        projects.mkdir(parents=True)
        for slug in ("minecraft", "work"):
            (projects / f"{slug}.conf").write_text(f"name={slug}\n")
        self.run_ctx("service", "minecraft", "minecraft-mm.service")

    def script(self, path, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
        path.chmod(0o700)

    def run_ctx(self, *args, ok=True):
        result = subprocess.run(["bash", str(CLI), *args], env=self.env,
                                capture_output=True, text=True, timeout=5)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def current(self):
        path = self.config / "state" / "current"
        return path.read_text().strip() if path.exists() else None

    def events(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_switch_order_and_same_context_noop(self):
        self.run_ctx("switch", "minecraft")
        before = self.events()
        self.run_ctx("switch", "minecraft")
        self.assertEqual(self.events(), before)
        self.run_ctx("switch", "work")
        self.assertEqual(self.events(), ["start minecraft", "--user start -- minecraft-mm.service",
                         "checkpoint minecraft", "--user stop -- minecraft-mm.service",
                         "stop ", "start work"])
        self.assertEqual(self.current(), "work")

    def test_exit_archive_and_delete_stop_service(self):
        for command in ("exit", "archive", "delete"):
            with self.subTest(command=command):
                self.run_ctx("switch", "minecraft")
                args = () if command == "exit" else ("minecraft",)
                self.run_ctx(command, *args)
                self.assertIsNone(self.current())
                self.assertEqual(self.events()[-3:], ["checkpoint minecraft",
                                 "--user stop -- minecraft-mm.service", "stop "])
                if command == "archive":
                    self.run_ctx("unarchive", "minecraft")
        self.assertFalse((self.config / "hooks" / "minecraft").exists())

    def test_stop_failure_keeps_old_context_and_blocks_switch(self):
        self.run_ctx("switch", "minecraft")
        (self.root / "fail-stop").touch()
        self.run_ctx("switch", "work", ok=False)
        self.assertEqual(self.current(), "minecraft")
        self.assertNotIn("start work", self.events())
        (self.root / "fail-stop").unlink()
        self.run_ctx("exit")

    def test_enter_failure_cleans_up(self):
        (self.root / "fail-start").touch()
        # Let daemon monitoring start, but fail systemctl start.
        self.script(self.root / "bin" / "ctxdctl", '''
[[ "$1" == ping ]] && exit 0
printf '%s %s\n' "$1" "${2:-}" >> "$TEST_LOG"
''')
        self.run_ctx("switch", "minecraft", ok=False)
        self.assertIsNone(self.current())
        self.assertEqual(self.events()[-2:], ["--user stop -- minecraft-mm.service", "stop "])

    def test_enter_and_cleanup_failure_retains_retry_target(self):
        self.script(self.config / "hooks" / "minecraft" / "enter", "exit 1\n")
        self.script(self.config / "hooks" / "minecraft" / "leave", "exit 1\n")
        self.run_ctx("switch", "minecraft", ok=False)
        self.assertEqual(self.current(), "minecraft")

    def test_checkpoint_failure_does_not_stop_service(self):
        self.run_ctx("switch", "minecraft")
        (self.root / "fail-checkpoint").touch()
        self.run_ctx("exit", ok=False)
        self.assertEqual(self.current(), "minecraft")
        self.assertNotIn("--user stop -- minecraft-mm.service", self.events())

    def test_service_does_not_overwrite_hooks_or_allow_invalid_paths(self):
        self.run_ctx("service", "minecraft", "other.service", ok=False)
        self.run_ctx("switch", "../minecraft", ok=False)
        self.run_ctx("service", "work", "--bad.service", ok=False)

    def test_generic_hooks_receive_context_environment(self):
        self.script(self.config / "hooks" / "work" / "enter",
                    'printf "%s %s\\n" "$CTX_CONTEXT" "$CTX_EVENT" >> "$TEST_LOG"\n')
        self.run_ctx("switch", "work")
        self.assertIn("work enter", self.events())


if __name__ == "__main__":
    unittest.main()
