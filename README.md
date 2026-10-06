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
ctx archive <context>      Checkpoint if active, then archive it
ctx unarchive <context>    Restore an archived context to the active list
ctx delete <context>       Delete a context and its saved state
```

`ctx new` asks only for a name when one is not provided. It does not ask which apps or folders belong to the context. The context learns its contents from the session itself.

## Monitoring model

`ctxd` is the user-session daemon. `ctxdctl` communicates with it over a Unix socket.

When monitoring starts, live state is cleared. When a context is checkpointed, the daemon writes:

```text
~/.config/ctx/state/<context>/snapshot.json
```

The snapshot contains generic desktop/process information plus state reported by application adapters. Updates sent while monitoring is stopped are ignored.

Application-specific capture is adapter-oriented. Executables named like these can contribute JSON to a snapshot:

```text
ctx-capture-firefox
ctx-capture-obsidian
ctx-capture-vscode
```

Missing applications or adapters are not errors. This allows different machines to participate in the same context system without having identical software installed.

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

A future configuration can therefore grow naturally without changing the base import:

```nix
programs.contextSwitcher = {
  enable = true;

  integrations = {
    firefox.enable = true;
    obsidian.enable = true;
    vscode.enable = true;
  };

  sync.enable = true;
};
```

The repository is now intended to be consumed as infrastructure, not copied into each machine configuration.
