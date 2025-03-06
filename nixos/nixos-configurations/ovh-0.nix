{
  inputs,
  lib,
  pkgs,
  config,
  ezModules,
  ...
}: {
  imports = [
    ezModules.ovh
    ezModules.k3s-overlay
  ];
  networking.interfaces.enp10s0f1np1 = {
    ipv4.addresses = [
      {
        address = "192.168.0.10";
        prefixLength = 24;
      }
    ];
    useDHCP = false;
  };
  services.k3s = {
    role = "server";
    extraFlags = lib.concatStringsSep " " [
      "--disable traefik"
      # "--docker"
      "--tls-san 164.132.247.36"
      "--flannel-iface enp10s0f1np1"
      "--node-ip=192.168.0.10"
      "--kubelet-arg=eviction-hard=nodefs.available<1%,imagefs.available<1%,nodefs.inodesFree<1%"
    ];
  };
}
