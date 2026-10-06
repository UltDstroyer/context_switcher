# Adapters

Application-specific context capture and restore integrations live here.

The core daemon should remain application-agnostic. Capture adapters are discovered as executables named:

```text
ctx-capture-<name>
```

Each capture adapter writes valid JSON to stdout and exits successfully when it can provide state. If the relevant application is not installed or not running, the adapter should fail quietly or return an empty state without breaking the overall checkpoint.

Restore adapters will follow the corresponding convention:

```text
ctx-restore-<name>
```

Keeping this boundary stable means Firefox, Obsidian, VS Code, KDE, terminal, and future integrations can evolve independently of the CLI and daemon.
