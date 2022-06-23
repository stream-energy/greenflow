{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  # nativeBuildInputs is usually what you want -- tools you need to run
  nativeBuildInputs = with pkgs; [
    # System
    wget

    # Nix stuff
    nixpkgs-fmt
    rnix-lsp
    comma
    nix-index

    # Python stuff
    python3
    poetry

    # QoL
    fish
    lsd
    fzf
    bat

    # Infra
    ansible
    kubernetes-helm-wrapped
    helmfile
    kubectl
  ];
}
