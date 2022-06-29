{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    hello

    # keep this line if you use bash
    # pkgs.bashInteractive
    nixpkgs-fmt
  ];
}
