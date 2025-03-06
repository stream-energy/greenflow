{
  inputs,
  lib,
  pkgs,
  ...
}: let
  inherit (pkgs) system;
  inherit (inputs) nixpkgs-k3s-1_24;

  old_k3s = import nixpkgs-k3s-1_24 {inherit system;};
in {
  # create Nixpkgs overlay
  nixpkgs.overlays = [
    (final: prev: {
      k3s = old_k3s.k3s_1_24;
    })
  ];
  systemd.services.shutdown-k3s = {
    description = "Kill containerd-shims on shutdown";
    unitConfig = {
      DefaultDependencies = false;
      Before = ["shutdown.target" "umount.target"];
    };
    serviceConfig = {
      Type = "oneshot";
      ExecStart = "${old_k3s.k3s_1_24}/bin/k3s-killall.sh";
    };
    wantedBy = ["shutdown.target"];
  };
}
