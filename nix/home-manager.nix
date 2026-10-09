{ config, lib, pkgs, ... }:

let
  cfg = config.programs.contextSwitcher;
  integrations = import ./integrations.nix { inherit lib pkgs cfg; };

  integrationOptions = {
    firefox.enable = lib.mkEnableOption "Firefox context capture";
    obsidian.enable = lib.mkEnableOption "Obsidian context capture";
    vscode.enable = lib.mkEnableOption "VS Code/VSCodium context capture";
    kde.enable = lib.mkEnableOption "KDE Plasma context capture";
  };
in
{
  options.programs.contextSwitcher = {
    enable = lib.mkEnableOption "Context Switcher";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ../package.nix { };
      defaultText = lib.literalExpression "pkgs.callPackage ../package.nix { }";
      description = "The Context Switcher package to install.";
    };

    daemon.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Whether to run ctxd as a systemd user service.";
    };

    integrations = integrationOptions;
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ cfg.package ] ++ integrations.selected;
    
    # Automatically register the local native-messaging bridge for Firefox.
    home.file.".mozilla/native-messaging-hosts/org.ctx_switcher.firefox.json" =
      lib.mkIf cfg.integrations.firefox.enable {
        text = builtins.toJSON {
          name = "org.ctx_switcher.firefox";
          description = "Local Firefox bridge for Context Switcher";
          path = "${cfg.package}/bin/ctx-firefox-host";
          type = "stdio";
          allowed_extensions = [ "context-switcher@local" ];
        };
      };


    systemd.user.services.context-switcher = lib.mkIf cfg.daemon.enable {
      Unit = {
        Description = "Context Switcher capture daemon";
      };

      Service = {
        ExecStart = "${cfg.package}/bin/ctxd";
        Restart = "on-failure";
        RestartSec = 2;
        Environment = [
          "PATH=${integrations.path}:${cfg.package}/bin:/run/current-system/sw/bin"
        ];
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };
  };
}
