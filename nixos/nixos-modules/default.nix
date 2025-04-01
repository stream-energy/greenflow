{
  pkgs,
  lib,
  inputs,
  ...
}: {
  imports = [
    # ../common
    inputs.lollypops.nixosModules.lollypops
    inputs.disko.nixosModules.disko
  ];
  lollypops.deployment = {
    config-dir = "/etc/lollypops";
    local-evaluation = true;
    deploy-method = "archive";
  };
  # services.dbus.enable = false;

  #TODO: Add ulimits infinite files
  # security.pam.loginLimits = [
  #   { domain = "*"; item = "nofile"; type = "-"; value = "32768"; }
  #   { domain = "*"; item = "memlock"; type = "-"; value = "32768"; }
  # ];

  time.timeZone = "Europe/Paris";
  networking.nameservers = lib.mkDefault ["1.1.1.1" "8.8.4.4"];
  networking = {
    # enableIPv6 = false;
    firewall = {
      enable = lib.mkDefault false;
      # allowedTCPPorts = lib.mkForce [80 443];
    };
  };
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";

  # virtualisation = {
  # podman = {
  #   enable = true;
  #   dockerSocket.enable = true;
  #   dockerCompat = true;
  # };
  # docker = {
  #   enable = true;

  #   # https://github.com/NixOS/nixpkgs/issues/182916#issuecomment-1364504677
  #   liveRestore = false;
  #   # listenOptions = ["/run/docker.sock"];
  # };
  #   containers = {
  #     enable = true;
  #     policy = {
  #       default = [{type = "insecureAcceptAnything";}];
  #       transports = {
  #         docker-daemon = {"" = [{type = "insecureAcceptAnything";}];};
  #       };
  #     };
  #   };
  # };
  services = {
    vnstat.enable = true;
    eternal-terminal.enable = true;
    logind.lidSwitch = "ignore";
    openssh = {
      enable = true;
      settings.PermitRootLogin = "yes";
    };
  };
  # services.restic.backups = {
  #   persistBackup = {
  #     paths = ["/persist"];
  #     repository = "s3:https://s3.eu-west-2.wasabisys.com/a-restic0";
  #     passwordFile = "/path/to/restic-password-file";
  #     environmentFile = "/path/to/restic-environment-file";
  #     initialize = true;
  #     pruneOpts = [
  #       "--keep-daily 7"
  #       "--keep-weekly 4"
  #       "--keep-monthly 6"
  #     ];
  #     timerConfig = {
  #       OnCalendar = "daily";
  #       RandomizedDelaySec = "1h";
  #       Persistent = true;
  #     };
  #   };
  # };

  environment.systemPackages = with pkgs; [
    openssh
    k3s
    kubectl
  ];

  # environment.etc."ssh/authorized_keys".source = ../authorized_keys;
  users.users = {
    # g = {
    #   isNormalUser = true;
    #   extraGroups = ["wheel" "docker"];
    #   uid = 1000;
    #   group = "g";
    #   hashedPassword = "$y$j9T$EGciD4ry3k6JNIStFd93S/$Qy64SVSrk7xsPcjWhHj1uHnzwkiaAzcwrjIzC.qoZL6";
    #   shell = pkgs.zsh;
    #   openssh.authorizedKeys.keyFiles = [../authorized_keys];
    # };
    gkovilkkattpanickerveetil = {
      isNormalUser = true;
      extraGroups = ["wheel" "docker"];
      uid = 1000;
      group = "gkovilkkattpanickerveetil";
      hashedPassword = "$y$j9T$EGciD4ry3k6JNIStFd93S/$Qy64SVSrk7xsPcjWhHj1uHnzwkiaAzcwrjIzC.qoZL6";
      shell = pkgs.zsh;
      openssh.authorizedKeys.keyFiles = [../authorized_keys];
    };
    root = {
      hashedPassword = "$y$j9T$EGciD4ry3k6JNIStFd93S/$Qy64SVSrk7xsPcjWhHj1uHnzwkiaAzcwrjIzC.qoZL6";
      shell = pkgs.zsh;
      openssh.authorizedKeys.keyFiles = [../authorized_keys];
    };
  };
  programs = {
    zsh.enable = true;
    nix-ld.enable = true;
  };
  users.groups = {gkovilkkattpanickerveetil = {gid = 1000;};};
  security.sudo.wheelNeedsPassword = false;

  system.stateVersion = "24.11";
}
