{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/release-24.11";
    nixpkgs-k3s-1_24.url = "github:NixOS/nixpkgs/0e7f98a5f30166cbed344569426850b21e4091d4";

    flake-root.url = "github:srid/flake-root";
    deploy-rs.url = "github:serokell/deploy-rs";
    nix-index-database.url = "github:nix-community/nix-index-database";
    nix-index-database.inputs.nixpkgs.follows = "nixpkgs";

    ez-configs = {
      url = "github:ehllie/ez-configs";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-parts.follows = "flake-parts";
      };
    };
    disko.url = "github:nix-community/disko";
    nixos-generators = {
      url = "github:nix-community/nixos-generators";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    lollypops.url = "github:pinpox/lollypops";
  };

  outputs = inputs @ {
    self,
    flake-parts,
    lollypops,
    deploy-rs,
    ...
  }:
    flake-parts.lib.mkFlake {inherit inputs;} {
      debug = true;
      imports = [
        inputs.flake-root.flakeModule
        inputs.ez-configs.flakeModule
      ];

      systems = [
        "aarch64-linux"
        "x86_64-linux"
        "aarch64-darwin"
        "x86_64-darwin"
      ];

      ezConfigs = {
        root = ./.;
        globalArgs = {
          inherit inputs;
          inherit self;
        };
      };
      perSystem = {
        pkgs,
        lib,
        system,
        self',
        ...
      }: {
        apps.default = inputs.lollypops.apps."${system}".default {configFlake = self;};
        # checks = builtins.mapAttrs (system: deployLib: deployLib.deployChecks self.deploy) deploy-rs.lib;

        devShells.default = pkgs.mkShell {
          name = "default-shell";
          packages = with pkgs;
            [
              home-manager
              age
              cloudflared
              sops
              ssh-to-age
              nix
              pkgs.deploy-rs
              python312
              python312Packages.pyyaml
              just
            ]
            ++ lib.optionals pkgs.stdenv.isLinux [
              nixos-rebuild
            ]
            ++ lib.optionals pkgs.stdenv.isDarwin [
              inputs.darwin.packages.${system}.default
            ];
        };
      };
    };
}
