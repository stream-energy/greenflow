{ pkgs ? import <nixpkgs> { } }:
let
  # my-python = pkgs.python3;
  # python-with-pkgs = my-python.withPackages (p: with p; [
  #   enoslib
  # ]);
in
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
    # python-with-pkgs
    python39
    poetry

    # QoL
    fish
    lsd
    fzf
    bat

    # Infra
    ansible
    kubernetes-helm
    helmfile
    kubectl
    kube3d
    docker
  ];
}
