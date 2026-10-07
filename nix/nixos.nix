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
      description = "Whether to provide ctxd as a systemd user service.";
    };

    integrations = integrationOptions;
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ] ++ integrations.selected;

    systemd.user.services.context-switcher = lib.mkIf cfg.daemon.enable {
      description = "Context Switcher capture daemon";
      wantedBy = [ "default.target" ];

      environment.PATH = lib.mkForce "${integrations.path}:${cfg.package}/bin:/run/current-system/sw/bin";

      serviceConfig = {
        ExecStart = "${cfg.package}/bin/ctxd";
        Restart = "on-failure";
        RestartSec = 2;
      };
    };
  };
}
