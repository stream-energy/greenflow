{
  inputs,
  lib,
  pkgs,
  config,
  ezModules,
  ...
}: let
  name = "grappe-10";
  site = "nancy";
  # Define primary nameserver based on site
  primaryNameserver =
    if site == "nancy"
    then "172.16.79.106"
    else if site == "lyon"
    then "172.16.63.113"
    else "172.16.63.113";

  nameservers = [primaryNameserver "1.1.1.1"];
  networking = {
    # hostName = name;
    nameservers = nameservers;
    search = ["${site}.grid5000.fr" "grid5000.fr"];
    domain = "${site}.grid5000.fr";
  };
in {
  imports = [
    ezModules.aws-base
    ezModules.k3s-overlay
    inputs.nixos-generators.nixosModules.all-formats
  ];
  networking.hostName = "";
}
