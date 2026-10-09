# Context Switcher + local AI agent

The main repository owns the generic Extension API v1 router. The AI-specific
command adapter, named ctx-ext-agent, lives entirely in local-ai-agent.
See docs/EXTENSIONS.md for the reusable interface.

## Responsibilities

- Context Switcher manages context selection, lifecycle hooks, and snapshots.
- ctx-agent owns queued tasks, Ollama, memory, execution and approvals.
- ctx runs ctx-ext-agent from PATH. The extension then dispatches to its own
  ctx-agent and ctx-agent-media commands. Core ctx does not know AI subcommands.
- Jobs CONTINUE when you switch or exit contexts. Only future commands target
  the newly selected project.
- Project names default to the currently active ctx slug, or explicitly
  supplied --project name. This does not auto-import or auto-create projects.
- AI code edits remain inside disposable agent workspaces until an operator
  invokes ctx agent apply JOB_ID. This updates the **agent-managed imported
  copy** under /var/lib/ctx-agent/projects, NOT the original source tree.
- OBS recording is owner-initiated, not passive background context capture.

## Install both NixOS components

The agent repo is private, so cloning to a local directory avoids asking
Nix to authenticate to GitHub separately.

1. Clone UltDstroyer/local-ai-agent and check out milestone-0-security
   under /home/lena/src/local-ai-agent (adjust for your NixOS username).
2. Add to your existing NixOS flake inputs:

       context-switcher.url = "github:UltDstroyer/context_switcher";
       ctx-agent.url = "path:/home/lena/src/local-ai-agent";

3. Import BOTH NixOS modules into your host's modules list:

       inputs.context-switcher.nixosModules.default
       inputs.ctx-agent.nixosModules.default

4. Set these options in your host NixOS configuration:

       programs.contextSwitcher.enable = true;
       services.ctxAgent = {
         enable = true;
         operatorUsers = [ "lena" ];
         manageOllama = true;
         model = "qwen3:8b";
         gpuBackend = "rocm";
       };

   Set manageOllama = false if you already manage Ollama elsewhere.
   Do not separately enable context-switcher in Home Manager for the
   same user if NixOS already manages its user daemon.

5. Review your changed Nix configuration. Update the flake lock and rebuild
   with your usual nixos-rebuild process. Log out/in for group membership.
   Separately pull the model with ollama pull qwen3:8b.

6. Confirm the commands are installed:

       command -v ctx
       command -v ctx-agent
       ctx agent health

For local checkouts of both repositories, a path: flake input for
context_switcher works too. Pushing GitHub changes does not alter an
existing flake.lock or installed NixOS package automatically.

## Use

    ctx switch research
    ctx agent import ~/src/research-project
    ctx agent submit "Investigate the failing tests and propose a fix"
    ctx agent list
    ctx agent status JOB_ID
    ctx agent logs JOB_ID
    ctx agent diff JOB_ID
    ctx agent apply JOB_ID   # updates the agent-managed copy, not your live repo

    ctx agent mode quiet
    ctx agent mode balanced
    ctx agent mode maximum
    ctx agent pause
    ctx agent resume
    ctx agent note architecture "Project specific hints"
    ctx agent notes

    ctx agent media record start
    ctx agent media record stop

ctx agent import targets the current context slug. To avoid switching
contexts, use --project before the path or task:

    ctx agent import --project other ~/src/other-project
    ctx agent submit --project other "Run the Python test suite"

The desktop media commands are explicitly initiated and require separately
configuring OBS and an optional voice synthesis environment in the agent repo.

## Security and limitations

- ctx does not start the AI service automatically. The agent's NixOS module
  provides the separate systemd service.
- The ctx agent wrapper does not grant privilege elevation.
- Changes are only applied through explicit owner action.
- Voice and recording controls do not run as background ctx hooks.
- The agent is currently a preview. Its GPU modes are voluntary hints,
  not hard percentages. Real-home access, autonomous GUI control and ChatGPT
  remote access are not implemented.
- A source-code copy, not your live project, is exposed to AI tool calls.
- There is not yet a conflict-safe export/sync command to copy changes back
  to the original Git checkout. Apply is limited to the agent-managed copy.
- Without the agent extension installed, ctx agent gives a missing-extension
  error, while the rest of ctx still works. All add-ons are opt-in.

## Test

    python3 -m unittest discover -s tests -v
    bash -n src/ctx src/ctxd src/ctxdctl

The core tests use fake ctx-ext-* executables to verify generic dispatch.
Agent-specific argument parsing is tested in local-ai-agent. A live NixOS
check is still needed to verify the real Unix socket and Ollama.
