# Context extension interface v1

## Architecture

Context Switcher is the main platform. It owns named contexts, lifecycle
coordination, context snapshots, and the stable ctx command.

Independent repositories own optional features. The main repo has no
hardcoded knowledge of AI models, video production or any future extensions.

    context_switcher (core)
      ctx / ctxd / ctxdctl
        |
        +-- ctx agent ... --> ctx-ext-agent (local-ai-agent repository)
        +-- ctx hello ... --> ctx-ext-hello (example)
        +-- ctx <other> ... --> ctx-ext-<other> (future repository)

An extension is installed by adding an executable named ctx-ext-ID to PATH.
ID must match ^[a-z][a-z0-9-]{0,47}$. Built-in ctx commands take precedence.
No registration file or edit to the context_switcher repo is needed.

## Runtime interface

Invocation:

    ctx <ID> <arg1> ...

runs:

    ctx-ext-<ID> <arg1> ...

The core forwards arguments unmodified and provides environment variables:

- CTX_EXTENSION_API_VERSION=1
- CTX_CONTEXT=active slug (empty when no active context)
- CTX_CONFIG_ROOT=absolute current ctx configuration directory

Extensions must treat CTX_CONTEXT as a *hint*, not an authorization token.
They handle their own help, options, approvals, files, model and services.
They must validate project names and paths before using them.

Core does not install/launch background workers as a side-effect of invoking
an extension. It releases its lifecycle flock before running add-on programs,
so an extension can take time without blocking context switches.

To list installed add-ons, run:

    ctx extensions

The listing examines executable ctx-ext-* names in PATH, without running
their code. Plugins lacking a matching executable are not discovered.
A plugin can also run standalone without Context Switcher.

## Trust model

Add-ons are executable programs running with the invoker's privileges,
just like other commands installed from a Nix package. Installing an
untrusted add-on can compromise its user's data. The core does not sandbox
or audit third-party executables. Individual add-ons must enforce their
own security boundaries and request separate approval for sensitive actions.

The extension protocol gives no root authority, implicit access to active
windows, network credentials, agent-policy modification, or unattended recording.
A plugin can only use authority already granted by the OS/user.

The existing per-context enter/leave hooks are separate and continue to
work; no extension is auto-registered as a lifecycle hook. Later optional
event subscriptions should require owner-configured enablement.

## NixOS extension installation pattern

The core flake requires no other extension repositories as inputs.
Each add-on has its own flake, NixOS or Home Manager module, and package.

Example:

    inputs.context-switcher.url = "github:UltDstroyer/context_switcher";
    inputs.agent-extension.url = "path:/home/lena/src/local-ai-agent";

Import both independent modules where desired:

    inputs.context-switcher.nixosModules.default
    inputs.agent-extension.nixosModules.default

Enable the individual modules:

    programs.contextSwitcher.enable = true;
    services.ctxAgent.enable = true;

The agent package installs ctx-ext-agent alongside ctx-agent commands.
If the agent extension is not installed, ctx still works normally.

## Add-on checklist

1. Choose an ID that doesn't shadow core built-ins.
2. Publish ctx-ext-ID as an executable in your add-on package.
3. Handle --help and return meaningful exit codes.
4. Read CTX_CONTEXT only as optional context; support an explicit project.
5. Keep plugin state within its own directories, not inside core state.
6. Keep permissions / approvals in the add-on service, not shell parsing.
7. Add standalone tests and mock core dispatch integration tests.
8. Avoid callbacks into ctx while holding locks; ctx releases its lock.
9. Declare compatibility with Extension API v1 in docs/manifest.
10. Only use lifecycle hooks through opt-in existing context hooks.

The agent repository is the reference extension implementation.
