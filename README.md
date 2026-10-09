# context_switcher

A portable Linux work-context manager designed to be consumed directly as a Nix flake.

A context is created from only a name. Entering it starts monitoring, and leaving it checkpoints the current desktop/application state. Activity while no context is active is not attributed to any context.

## Repository contract

The repository is structured so other Nix configurations can import it without knowing how the implementation is organized internally.

Stable flake outputs:

```text
packages.<system>.default
packages.<system>.context-switcher
apps.<system>.default
apps.<system>.ctx
overlays.default
homeManagerModules.default
homeManagerModules.context-switcher
nixosModules.default
nixosModules.context-switcher
```

The intended stable user-facing option is:

```nix
programs.contextSwitcher.enable = true;
```

That interface should stay stable even if the shell scripts, adapters, or daemon implementation are replaced later.

## Import into an existing NixOS flake

Add Context Switcher as an input:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    context-switcher = {
      url = "github:UltDstroyer/context_switcher";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };
}
```

### NixOS module

Import the module in your NixOS configuration:

```nix
{
  inputs,
  ...
}:

{
  imports = [
    inputs.context-switcher.nixosModules.default
  ];

  programs.contextSwitcher = {
    enable = true;
  };
}
```

This installs `ctx`, `ctxd`, and `ctxdctl` system-wide and provides the daemon as a systemd user service.

### Home Manager module

If you manage user applications through Home Manager, import:

```nix
{
  inputs,
  ...
}:

{
  imports = [
    inputs.context-switcher.homeManagerModules.default
  ];

  programs.contextSwitcher = {
    enable = true;

    daemon.enable = true;

    integrations = {
      firefox.enable = true;
      obsidian.enable = true;
      vscode.enable = true;
      kde.enable = true;
    };
  };
}
```

For a personal desktop configuration, Home Manager is likely to become the preferred integration because Context Switcher operates on the graphical user session rather than as a privileged system service.

Do not enable both modules for the same user unless there is a specific reason to do so.

## Use without installing

Run the CLI directly from GitHub:

```bash
nix run github:UltDstroyer/context_switcher
```

Open a development shell:

```bash
nix develop github:UltDstroyer/context_switcher
```

Build the package:

```bash
nix build github:UltDstroyer/context_switcher
```

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
ctx service <context> <unit> Attach a systemd user service to a context
ctx archive <context>      Checkpoint if active, then archive it
ctx unarchive <context>    Restore an archived context to the active list
ctx delete <context>       Delete a context and its saved state
```

`ctx new` asks only for a name when one is not provided. It does not ask which apps or folders belong to the context. The context learns its contents from the session itself.

## Context lifecycle hooks and Minecraft

Executable hooks live in `$XDG_CONFIG_HOME/ctx/hooks/<context>/enter` and
`leave` (default: `~/.config/ctx/hooks/<context>/`). Context metadata is still
plain data; it is never sourced as shell code. Hooks are optional and run as
scripts with `CTX_CONTEXT`, `CTX_EVENT`, and `CTX_CONFIG_ROOT` in their environment.
Use hooks only for programs you trust. Do not call lifecycle-changing `ctx`
commands inside hooks: those commands wait for the lifecycle lock held by the caller.

Entry starts monitoring, runs `enter`, then records the active context. Leaving
checkpoints the context, runs `leave`, stops monitoring, then clears the active
context. This applies to switching away, `exit`, and archiving or deleting the
active context. Archiving preserves hooks; deletion removes them. Concurrent CLI
operations are serialized so a new context cannot start while the previous
service is still stopping. Selecting an already active context is a no-op.

A failed leave hook cancels the transition and retains the old context for retry.
A failed enter hook invokes the destination's leave hook to clean up partial
startup, and leaves no active context if cleanup succeeds. If cleanup also fails,
the destination stays active so `ctx exit` can retry. Hooks should be idempotent.

### Attach the existing Minecraft user service

After updating your Nix flake input and rebuilding, first leave any active
context. Use `ctx list` to find the existing Minecraft context's slug. If you do
not have one yet, create it with `ctx new Minecraft`, then run `ctx exit`.
Assuming its slug is `minecraft`:

```bash
ctx service minecraft minecraft-mm.service
ctx switch minecraft
```

`ctx service` writes two machine-local hooks that run:

```bash
systemctl --user start -- minecraft-mm.service
systemctl --user stop -- minecraft-mm.service
```

It refuses to overwrite existing hooks or configure the currently active context.
The service's existing systemd/RCON shutdown owns saving and stopping Minecraft;
ctx does not send RCON commands or kill Java itself. Systemctl waits for the stop
job to complete before ctx finishes leaving. Startup completion follows the
service's configured systemd Type; it is not necessarily Minecraft readiness.

Test on your machine:

```bash
systemctl --user status minecraft-mm.service
ctx exit
systemctl --user status minecraft-mm.service
journalctl --user -u minecraft-mm.service -n 40 --no-pager
```

For a configuration flake in `/etc/nixos` with an input named `context-switcher`:

```bash
cd /etc/nixos
sudo nix flake update context-switcher
sudo nixos-rebuild switch --flake .
```

Use your usual rebuild target if your configuration requires `.#<hostname>`.
Updating the repo does not automatically update an existing `flake.lock` or the
installed Nix-managed ctx. Keep using the packaged executable; do not copy it
into `~/.local/bin` or edit `/nix/store`.

### Validation

Run the lifecycle tests without real services:

```bash
python3 -m unittest discover -s tests -v
bash -n src/ctx src/ctxd src/ctxdctl
```

## Monitoring model

`ctxd` is the user-session daemon. `ctxdctl` communicates with it over a Unix socket.

When monitoring starts, live state is cleared. When a context is checkpointed, the daemon writes:

```text
~/.config/ctx/state/<context>/snapshot.json
```

The snapshot contains generic desktop/process information plus state reported by application adapters. Updates sent while monitoring is stopped are ignored.

### Firefox native tab capture (development MVP)

The Firefox integration now includes an extension under `firefox-extension/`
and a Python native-messaging bridge under `native-host/`. The existing
`ctx-capture-firefox` adapter still captures generic process/window state,
while the extension contributes tab/window data to
`snapshot.json` under `.live_updates.firefox`.

On NixOS, enable `programs.contextSwitcher.integrations.firefox.enable = true;`
and rebuild, then run `ctx-firefox-register` as your normal user.
Home Manager registers the host automatically when Firefox capture is enabled.
Load `firefox-extension/manifest.json` from `about:debugging` for development.
This temporary extension is removed on Firefox restart.

See [Firefox integration setup and limitations](firefox-extension/README.md).
Native messaging only operates locally, and `ctxd` checks the context on
every Firefox update. It does not capture private windows or page contents.
A persistent Firefox extension still requires Mozilla signing, and reliable
leave-time flush/restore remains follow-up work.

Application-specific capture is adapter-oriented. The Nix modules can install adapters independently:

```nix
programs.contextSwitcher.integrations = {
  firefox.enable = true;
  obsidian.enable = true;
  vscode.enable = true;
  kde.enable = true;
};
```

Each enabled integration contributes a `ctx-capture-<name>` executable to the daemon's PATH. The current first-pass adapters capture whether the application/session component is running plus matching process and window metadata. They intentionally do not pretend to understand application-native session formats yet.

```text
ctx-capture-firefox
ctx-capture-obsidian
ctx-capture-vscode
ctx-capture-kde
```

Missing or disabled adapters are not errors. This lets a laptop, desktop, or future device use the same logical contexts without requiring identical software.

Applications and future integrations can also report state directly:

```bash
ctxdctl update firefox '{"tabs":[...]}'
```

Restore adapters will use the complementary naming convention:

```text
ctx-restore-firefox
ctx-restore-obsidian
ctx-restore-vscode
```

## Repository layout

```text
context_switcher/
├── flake.nix
├── package.nix
├── src/
│   ├── ctx
│   ├── ctxd
│   └── ctxdctl
├── adapters/
│   ├── default.nix
│   └── README.md
├── nix/
│   ├── home-manager.nix
│   └── nixos.nix
└── install.sh
```

The important architectural boundary is:

```text
Nix interface
     │
     ▼
package + module
     │
     ▼
ctx / ctxd
     │
     ▼
adapter interface
     │
     ├── Firefox
     ├── Obsidian
     ├── VS Code
     ├── KDE
     └── future integrations
```

The implementation behind those boundaries can change without forcing every machine that imports the flake to change its configuration.

## Current non-Nix install

The old bootstrap path remains available while development continues:

```bash
./install.sh
```

It installs the three scripts into `~/.local/bin`.

The Nix package supplies its own runtime dependencies, so machines consuming the flake do not need to manually install `jq`, `socat`, `wmctrl`, or the other command-line dependencies used by the scripts.

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

## Architectural direction

From here, development should happen behind the import interface instead of changing how machines consume the project.

Planned layers:

1. Keep capture and restore logic behind adapters.
2. Add first-class Firefox, Obsidian, VS Code, terminal, and KDE integrations.
3. Add module options for enabling individual integrations.
4. Separate logical context metadata from machine-local application state.
5. Add device identity to saved state.
6. Add optional synchronization between NixOS machines.
7. Eventually allow contexts to restore work intelligently on a machine that does not have exactly the same applications as the machine that captured them.

The integration interface is now live:

```nix
programs.contextSwitcher = {
  enable = true;

  integrations = {
    firefox.enable = true;
    obsidian.enable = true;
    vscode.enable = true;
    kde.enable = true;
  };
};
```

Future state capture can become richer behind those same switches. Planned additions include application-native restore adapters, device-aware state, terminals, and optional synchronization.

The repository is now intended to be consumed as infrastructure, not copied into each machine configuration.
