{
  pkgs,
  lib,
  config,
  inputs,
  ezModules,
  ...
}: {
  imports = [
    "${inputs.nixpkgs}/nixos/modules/virtualisation/amazon-image.nix"
    ./k3s-overlay.nix
  ];
  virtualisation.diskSize = 6 * 1024;

  hardware.enableRedistributableFirmware = true;
  hardware.firmware = [pkgs.firmwareLinuxNonfree];
  networking = {
    hostName = lib.mkDefault "";
    nameservers = lib.mkDefault ["1.1.1.1" "8.8.4.4"];
    firewall = {
      enable = lib.mkDefault false;
    };
  };

  services.cloud-init = {
    enable = true;
  };

  boot.initrd.availableKernelModules =
    if pkgs.stdenv.hostPlatform.isAarch64
    then ["nvme" "xhci_pci" "usbhid" "usb_storage" "sd_mod" "ena"]
    else ["nvme" "xhci_pci" "ahci" "sd_mod" "ena"];

  boot.kernelModules =
    if pkgs.stdenv.hostPlatform.isAarch64
    then ["ena"]
    else ["kvm-intel" "kvm-amd" "ena"];
}
