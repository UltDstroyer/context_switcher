{ lib, pkgs, cfg }:

let
  adapters = import ../adapters { inherit pkgs; };

  selected =
    lib.optionals cfg.integrations.firefox.enable [ adapters.firefox ]
    ++ lib.optionals cfg.integrations.obsidian.enable [ adapters.obsidian ]
    ++ lib.optionals cfg.integrations.vscode.enable [ adapters.vscode ]
    ++ lib.optionals cfg.integrations.kde.enable [ adapters.kde ];
in
{
  inherit adapters selected;
  path = lib.makeBinPath selected;
}
