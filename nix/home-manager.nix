{ config, lib, pkgs, ... }:

let
  cfg = config.programs.contextSwitcher;
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
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ cfg.package ];

    systemd.user.services.context-switcher = lib.mkIf cfg.daemon.enable {
      Unit = {
        Description = "Context Switcher capture daemon";
      };

      Service = {
        ExecStart = "${cfg.package}/bin/ctxd";
        Restart = "on-failure";
        RestartSec = 2;
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };
  };
}
