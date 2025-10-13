{
  pkgs,
  inputs,
  ...
}: {
  imports = [
    inputs.nixos-generators.nixosModules.all-formats
  ];
  services.cloud-init = {
    enable = true;
  };

  services.openssh.enable = true;
  documentation.doc.enable = false;
}
