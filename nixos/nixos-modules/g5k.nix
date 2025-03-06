{
  pkgs,
  lib,
  config,
  inputs,
  ezModules,
  ...
}: {
  imports = [
    inputs.nix-index-database.nixosModules.nix-index
    ./k3s-overlay.nix
  ];

  nixpkgs.hostPlatform = "x86_64-linux";
  hardware.enableRedistributableFirmware = true;
  hardware.firmware = [pkgs.firmwareLinuxNonfree];
  powerManagement.cpuFreqGovernor = "performance";

  # Since we are using kexec within the g5k KADeploy environment, we can disable bootloader installation
  boot.loader.systemd-boot.enable = false;
  boot.loader.grub.enable = lib.mkForce false;
  programs.nix-index-database.comma.enable = true;
  environment.systemPackages = with pkgs; [
    python3Minimal
    k3s
  ];

  boot.initrd.availableKernelModules = ["nvme" "ahci" "xhci_pci" "usb_storage" "usbhid" "sr_mod"];
  boot.initrd.kernelModules = [];
  boot.kernelModules = ["kvm-amd"];
  boot.extraModulePackages = [];

  fileSystems."/" = {
    device = "/dev/root";
    autoResize = true;
    fsType = "ext4";
  };
  fileSystems."/tmp" = {
    device = "/dev/disk/by-partlabel/KDPL_TMP_disk0";
    fsType = "ext4";
  };
}
