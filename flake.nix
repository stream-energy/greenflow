{
  description = "Description for the project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    devenv.url = "github:cachix/devenv";
    nix2container.url = "github:nlewo/nix2container";
    nix2container.inputs.nixpkgs.follows = "nixpkgs";
    mk-shell-bin.url = "github:rrbutani/nix-mk-shell-bin";
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      imports = [
        inputs.devenv.flakeModule
      ];
      debug = true;
      systems = ["x86_64-linux" "i686-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin"];

      perSystem = {
        config,
        self',
        inputs',
        pkgs,
        system,
        ...
      }: let
        _ = 0;
      in {
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

          packages = with pkgs; [
            sshpass
            dhall
            micromamba
            alejandra
            nil
            kubectl
            kubernetes-helm
            ruff
            just
            time
            gcc
            kube3d
            atuin
            kafkactl
            # redpanda-client
            fish
            (wrapHelm kubernetes-helm {
              plugins = with pkgs.kubernetes-helmPlugins; [
                helm-git
                helm-diff
              ];
            })
            direnv
            pulumi-bin
            mdbook
          ];
          scripts.resetEnv.exec = ''
            rm -rf .devenv
            rm -rf .mamba
            rm -rf .direnv
          '';
          scripts.firstTimeSetup.exec = ''
            git submodule update --recursive --init
            # Unset REQUESTS_CA_BUNDLE as we need to download pip packages
            export REQUESTS_CA_BUNDLE=

            # Python Stuff
            if ! [ -d "$PWD/.mamba" ]; then
              mkdir -p "$PWD/.mamba"
            fi
            micromamba install --platform linux-64 -y python=3.10 pip poetry -p ./.mamba -c conda-forge
            micromamba install --platform linux-64 -y -f env.yaml

            # Helm stuff
            helm repo add strimzi https://strimzi.io/charts/
            helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
            helm repo add grafana https://grafana.github.io/helm-charts
            helm repo add jetstack https://charts.jetstack.io
            helm repo add redpanda https://charts.redpanda.com
            helm repo update

            pushd $PWD/charts/redpanda-operator-helm/charts/redpanda
              helm dep build
            popd
            pushd $PWD/charts/prometheus-community/charts/kube-prometheus-stack
              helm dep build
            popd
            pushd $PWD/charts/theodolite/helm
              helm dep build
            popd
            ansible-galaxy collection install kubernetes.core
            ansible-galaxy collection install community.general

            # Create grid5000 creds file
            echo "
            username: $GRID5000_USERNAME
            password: $GRID5000_PASSWORD
            verify_ssl: $PWD/api-proxy-lille-grid5000-fr-chain.pem
            " > ~/.python-grid5000.yaml
            echo "
            - name: run_fio_benchmark
              src: https://github.com/mcharanrm/ansible-role-fio-benchmark.git
              version: origin/main
            " > /tmp/fio-requirements.yml
            ansible-galaxy install -r /tmp/fio-requirements.yml --roles-path $PWD/ansible/project/roles
          '';

          enterShell = ''
            export GITROOT="$(git rev-parse --show-toplevel)"
            export MAMBA_ROOT_PREFIX="''${GITROOT}/.mamba"
            eval "$(micromamba shell hook --shell=posix)"
            micromamba activate
          '';
        };
      };
    };
}
