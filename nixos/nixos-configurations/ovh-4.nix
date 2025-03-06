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
        address = "192.168.0.14";
        prefixLength = 24;
      }
    ];
    useDHCP = false;
  };
  services.k3s = {
    role = "agent";
    serverAddr = "https://192.168.0.10:6443";
    extraFlags = lib.concatStringsSep " " [
      "--node-ip=192.168.0.14"
      "--flannel-iface enp10s0f1np1"
      "--node-label=node.kubernetes.io/worker=true"
      "--kubelet-arg=eviction-hard=nodefs.available<1%,imagefs.available<1%,nodefs.inodesFree<1%"
    ];
  };
}
