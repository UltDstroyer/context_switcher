# context_switcher

A small Linux context manager for saving and switching between work contexts.

The current prototype is intentionally simple: a context is created from only a name, entering it starts monitoring, and leaving it checkpoints the current desktop/application state. Activity while no context is active is not attributed to any context.

This repository is the baseline for turning the tool into a native, declarative NixOS/Home Manager component.

## Current behavior

```text
ctx new [name]             Create and enter a context
ctx list                   List active contexts
ctx list --archived        List archived contexts
ctx list --all             List both
ctx current                Show the current context
ctx show [context]         Show context metadata and snapshot location
ctx edit [context]         Edit context metadata
ctx switch <context>       Enter a context and start monitoring
ctx exit                   Checkpoint the active context and stop monitoring
ctx archive <context>      Checkpoint if active, then archive it
ctx unarchive <context>    Restore an archived context to the active list
ctx delete <context>       Delete a context and its saved state
```

`ctx new` asks only for a name when one is not provided. It does not ask which apps or folders belong to the context. The goal is for the context to learn that from the session itself.

## Monitoring model

`ctxd` is the small user-session daemon. `ctxdctl` communicates with it over a Unix socket.

When monitoring starts, live state is cleared. When a context is checkpointed, the daemon writes:

```text
~/.config/ctx/state/<context>/snapshot.json
```

The current snapshot contains generic desktop window/process information plus state reported by application adapters. Updates sent while monitoring is stopped are ignored.

Application-specific capture is deliberately adapter-oriented. Executables named like these can contribute JSON to a snapshot:

```text
ctx-capture-firefox
ctx-capture-obsidian
ctx-capture-vscode
```

Missing applications/adapters are not errors. This lets different machines participate in the same context system without requiring identical software.

Applications or future integrations can also report state directly:

```bash
ctxdctl update firefox '{"tabs":[...]}'
```

## Files

```text
src/ctx       Main CLI
src/ctxd      Monitoring/checkpoint daemon
src/ctxdctl   Daemon control client
install.sh    Current non-declarative bootstrap installer
```

## Current install

For the prototype:

```bash
./install.sh
```

This installs the three scripts into `~/.local/bin`.

Required runtime dependency:

- `socat`

Recommended dependencies:

- `jq` for structured snapshots
- `wmctrl` for generic desktop-window capture

On NixOS these should eventually be supplied by the package itself instead of installed manually.

## State layout

```text
~/.config/ctx/
├── projects/
│   └── <context>.conf
├── archived/
│   └── <context>.conf
└── state/
    ├── current
    ├── monitoring
    ├── live/
    └── <context>/
        └── snapshot.json
```

The daemon socket lives under `$XDG_RUNTIME_DIR` when available.

## Direction

The next architectural steps are:

1. Keep the capture/restore logic behind small application adapters.
2. Package `ctx`, `ctxd`, and `ctxdctl` as one Nix derivation.
3. Add a Home Manager module that installs the package and creates a `systemd --user` service for `ctxd`.
4. Add optional integrations for Firefox, Obsidian, VS Code, terminals, and KDE.
5. Separate shared logical context data from device-local window/application state.
6. Add optional synchronization so the same logical contexts can exist across several NixOS devices.

The intended end state is roughly:

```nix
programs.contextSwitcher = {
  enable = true;

  integrations = {
    firefox.enable = true;
    obsidian.enable = true;
    vscode.enable = true;
  };
};
```

At that point a new NixOS machine should be able to acquire the context system through configuration rather than manual installation.
