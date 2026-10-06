{
  description = "Context Switcher: portable work-context capture for Linux and NixOS";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          contextSwitcher = pkgs.callPackage ./package.nix { };
        in
        {
          default = contextSwitcher;
          context-switcher = contextSwitcher;
        }
      );

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/ctx";
        };

        ctx = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/ctx";
        };
      });

      checks = forAllSystems (system: {
        package = self.packages.${system}.default;
      });

      devShells = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              jq
              shellcheck
              socat
              wmctrl
            ];
          };
        }
      );

      overlays.default = final: _prev: {
        context-switcher = final.callPackage ./package.nix { };
      };

      homeManagerModules = {
        default = import ./nix/home-manager.nix;
        context-switcher = self.homeManagerModules.default;
      };

      nixosModules = {
        default = import ./nix/nixos.nix;
        context-switcher = self.nixosModules.default;
      };
    };
}
