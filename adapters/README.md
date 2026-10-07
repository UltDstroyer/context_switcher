# Adapters

Application-specific context capture and restore integrations live here.

The core daemon remains application-agnostic. Nix installs only the adapters enabled for a machine and exposes them to `ctxd` through its service PATH.

## Stable executable contract

Capture:

```text
ctx-capture-<name>
```

Restore:

```text
ctx-restore-<name>
```

A capture adapter must:

1. Write exactly one valid JSON value to stdout.
2. Exit successfully when it can describe its state.
3. Avoid failing the whole checkpoint when its application is absent.
4. Include a `schema_version` so its state can evolve independently.

The initial adapters currently emit:

```json
{
  "schema_version": 1,
  "adapter": "firefox",
  "running": true,
  "processes": [],
  "windows": []
}
```

This first layer deliberately captures generic process/window state only. Application-native state such as Firefox tabs, Obsidian workspaces, or VS Code projects will be added inside the individual adapters rather than to `ctxd`.

## Current adapters

```text
firefox
obsidian
vscode
kde
```

They are independently exposed by the flake as:

```text
packages.<system>.adapter-firefox
packages.<system>.adapter-obsidian
packages.<system>.adapter-vscode
packages.<system>.adapter-kde
```

That makes an adapter independently testable without enabling it globally.

## Design rule

The daemon should know how to discover, invoke, validate, and store adapter output. It should not know how Firefox, Obsidian, KDE, or any other application represents its own state.

Keeping that boundary stable is what lets the internals evolve without changing the NixOS import surface.
