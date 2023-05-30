{
  description = "Description for the project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    devenv.url = "github:cachix/devenv";
    nix2container.url = "github:nlewo/nix2container";
    nix2container.inputs.nixpkgs.follows = "nixpkgs";
    mk-shell-bin.url = "github:rrbutani/nix-mk-shell-bin";
    myCertificate.url = "path:api-proxy-lille-grid5000-fr-chain.pem";
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      imports = [
        inputs.devenv.flakeModule
      ];
      systems = ["x86_64-linux" "i686-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin"];

      perSystem = {
        config,
        self',
        inputs',
        pkgs,
        system,
        ...
      }: {
        # Per-system attributes can be defined here. The self' and inputs'
        # module parameters provide easy access to attributes of the same
        # system.

        # Equivalent to  inputs'.nixpkgs.legacyPackages.hello;
        # packages.default = with pkgs; [
        #   hello
        #   micromamba
        # ];

        devenv.shells.default = {
          name = "greenflow";
          devcontainer = {
            enable = false;
            settings.updateContentCommand = "nix develop --impure";
            settings.customizations.vscode.extensions = [
              "charliermarsh.ruff"
              "kamadorueda.alejandra"
              "mkhl.direnv"
            ];
          };
          # languages.python = {
          #   enable = true;
          #   poetry = {
          #     enable = true;
          #     activate.enable = true;
          #   };
          # };

          # https://devenv.sh/reference/options/
          packages = with pkgs; [
            # python310
            micromamba
            alejandra
            kubectl
            kubernetes-helm
            ruff
            just
            time
            gcc
            kube3d
          ];
          scripts.firstTimeSetup.exec = ''
            eval "$(micromamba shell hook --shell=posix)"
            if ! [ -d "$PWD/.mamba" ]; then
              mkdir -p "$PWD/.mamba"
            fi
            micromamba activate
            micromamba install -y python=3.10 poetry pip -p ./.mamba -c conda-forge
            micromamba install -y -f env.yaml
            git config --global user.name Govind
            git config --global user.email git@govind.work
          '';

          enterShell = ''
            export REQUESTS_CA_BUNDLE=${inputs.myCertificate}

            export MAMBA_ROOT_PREFIX=$PWD/.mamba
            export KUBECONFIG=$PWD/kubeconfig
            eval "$(micromamba shell hook --shell=posix)"
            micromamba activate
          '';
        };
      };
      flake = {
        # The usual flake attributes can be defined here, including system-
        # agnostic ones like nixosModule and system-enumerating ones, although
        # those are more easily expressed in perSystem.
      };
    };
}
