{
  pkgs,
}:

let
  mkCaptureAdapter =
    {
      name,
      processPattern,
      windowPattern,
    }:
    pkgs.writeShellApplication {
      name = "ctx-capture-${name}";

      runtimeInputs = with pkgs; [
        coreutils
        gnugrep
        jq
        procps
        wmctrl
      ];

      text = ''
        processes="$(
          ps -u "$USER" -o pid=,comm=,args= 2>/dev/null \
            | grep -Ei -- ${pkgs.lib.escapeShellArg processPattern} \
            | grep -v -E 'ctx-capture-|grep -E' \
            || true
        )"

        windows="$(
          wmctrl -lx 2>/dev/null \
            | grep -Ei -- ${pkgs.lib.escapeShellArg windowPattern} \
            || true
        )"

        if [[ -n "$processes" ]]; then
          running=true
        else
          running=false
        fi

        jq -n \
          --arg adapter ${pkgs.lib.escapeShellArg name} \
          --argjson running "$running" \
          --arg processes "$processes" \
          --arg windows "$windows" \
          '{
            schema_version: 1,
            adapter: $adapter,
            running: $running,
            processes: ($processes | split("\n") | map(select(length > 0))),
            windows: ($windows | split("\n") | map(select(length > 0)))
          }'
      '';
    };
in
{
  firefox = mkCaptureAdapter {
    name = "firefox";
    processPattern = ''(^|[[:space:]/])(firefox|firefox-bin)([[:space:]]|$)'';
    windowPattern = ''firefox|navigator'';
  };

  obsidian = mkCaptureAdapter {
    name = "obsidian";
    processPattern = ''obsidian|electron.*obsidian'';
    windowPattern = ''obsidian'';
  };

  vscode = mkCaptureAdapter {
    name = "vscode";
    processPattern = ''(^|[[:space:]/])(code|codium)([[:space:]]|$)|visual studio code'';
    windowPattern = ''code|codium|visual studio code'';
  };

  kde = mkCaptureAdapter {
    name = "kde";
    processPattern = ''kwin_wayland|kwin_x11|plasmashell'';
    windowPattern = ''.'';
  };
}
