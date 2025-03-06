{
  pkgs,
  lib,
  config,
  inputs,
  ...
}: {
  imports = [
    inputs.nix-index-database.nixosModules.nix-index
  ];
  programs.nix-index-database.comma.enable = true;
  nixpkgs.hostPlatform = "x86_64-linux";
  hardware.cpu.amd.updateMicrocode = lib.mkDefault config.hardware.enableRedistributableFirmware;
  # In order to make use of intel ice NICs
  hardware.enableRedistributableFirmware = true;

  # Change the CPU governor
  powerManagement.cpuFreqGovernor = "performance";

  hardware.firmware = [pkgs.firmwareLinuxNonfree];

  boot.kernelParams = [
    "iommu=pt"
    # Keep any other kernel parameters you've already added
    # "ice.Nenable_rx_csum=1"
    # "ice.Nenable_tx_csum=1"
    # "ice.Nenable_l2_tso=1"
    # "ice.Nenable_l2_gro=1"
    # "ice.Nenable_rx_scatter=1"
    # "ice.Nenable_rss=1"
  ];

  boot.initrd.availableKernelModules = ["nvme" "ahci" "xhci_pci" "usb_storage" "usbhid" "sr_mod"];
  boot.initrd.kernelModules = [];
  boot.kernelModules = ["kvm-amd"];
  boot.extraModulePackages = [];

  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  environment.systemPackages = with pkgs; [
    python3Minimal
  ];
  disko.devices = {
    disk = {
      nvme1n1 = {
        type = "disk";
        device = "/dev/nvme1n1";
        content = {
          type = "gpt";
        };
      };
      nvme2n1 = {
        type = "disk";
        device = "/dev/nvme2n1";
        content = {
          type = "gpt";
        };
      };
      nvme3n1 = {
        type = "disk";
        device = "/dev/nvme3n1";
        content = {
          type = "gpt";
        };
      };
      nvme0n1 = {
        type = "disk";
        device = "/dev/nvme0n1";
        content = {
          type = "gpt";
          partitions = {
            boot = {
              size = "2G";
              type = "EF00";
              content = {
                type = "filesystem";
                format = "vfat";
                mountpoint = "/boot";
                mountOptions = [
                  "defaults"
                  "relatime"
                ];
              };
            };
            root = {
              size = "100%"; # Use remaining space
              content = {
                type = "filesystem";
                format = "ext4";
                mountpoint = "/";
                mountOptions = [
                  "defaults"
                  "relatime"
                ];
              };
            };
          };
        };
      };
    };
  };
}
