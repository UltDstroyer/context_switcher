# Firefox integration (development MVP)

This extension takes **local metadata-only snapshots** of Firefox tabs and
windows while a Context Switcher context is active. It does not inspect page
content, collect typing, capture screenshots, or send data to the internet.
Private windows are excluded.

## Installation on NixOS

Update your Nix flake input for `context-switcher` and rebuild, as described
in the root README. Enable Firefox capture:

```nix
programs.contextSwitcher = {
  enable = true;
  integrations.firefox.enable = true;
};
```

With the **NixOS module**, register the packaged native-messaging host once
as your normal desktop user, not with sudo:

```bash
ctx-firefox-register
```

This creates `~/.mozilla/native-messaging-hosts/org.ctx_switcher.firefox.json`.
After rebuilding to a new package revision, run this registration command
again to refresh the store path.

With the **Home Manager module**, the native-messaging host manifest is
managed automatically when `integrations.firefox.enable = true`.

For initial development, open Firefox's `about:debugging#/runtime/this-firefox`,
select **Load Temporary Add-on**, and choose
`firefox-extension/manifest.json` from your checkout. Temporary add-ons
must be reloaded after Firefox restarts. Regular Firefox generally requires
a Mozilla-signed extension for permanent installation; release signing is
a later milestone.

## Verify capture

```bash
ctxdctl ping
ctx new Firefox Test
# Open, move, or close a few Firefox tabs.
ctx exit
jq '.live_updates.firefox' ~/.config/ctx/state/firefox-test/snapshot.json
```

The Firefox toolbar popup reports the active context and lets you request
a resync. If the bridge is unavailable, check the popup and the daemon:

```bash
systemctl --user status context-switcher.service
ctxdctl status
cat ~/.mozilla/native-messaging-hosts/org.ctx_switcher.firefox.json
```

Your saved snapshots contain URLs and titles, which can be sensitive.
Context data stays in your local `~/.config/ctx/state` directory. Protect
that directory and avoid syncing it to an untrusted location.

## How it works

- Firefox uses `runtime.connectNative("org.ctx_switcher.firefox")`.
- The Python host reads/writes Firefox's length-prefixed JSON messages.
- The host uses the existing `ctxd.sock` Unix socket.
- `UPDATE_CTX\t<context>\tfirefox\t<json>` stores a snapshot only if
  the daemon is currently monitoring that exact context.
- The host reports ctx status changes roughly once per second, and
  Firefox sends debounced snapshots as tabs/windows change.
- `ctx exit` checkpoints the most recent acknowledged snapshot and
  stops capture.

**MVP limitation:** Very last-moment tab changes immediately before
`ctx exit` may not reach the daemon before checkpointing. Automatic
Firefox tab restoration, persistent signed installation, and guaranteed
leave-time flush are follow-up milestones. This MVP observes the currently
open Firefox workspace, not isolated browser windows per context.

## Developer checks

```bash
python3 -m unittest discover -s tests -v
bash -n src/ctx src/ctxd src/ctxdctl native-host/register.sh
node --check firefox-extension/background.js
node --check firefox-extension/popup/popup.js
```
