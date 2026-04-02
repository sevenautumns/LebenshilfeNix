{
  config,
  lib,
  modulesPath,
  ...
}:
{
  imports = [
    (modulesPath + "/profiles/qemu-guest.nix")
    ./certificate.nix
    ./nextcloud.nix
    ./postgresql.nix
    ./software.nix
    ./backup.nix
    ./lebenshilfe-cms.nix
  ];

  boot.tmp.cleanOnBoot = true;
  boot.loader.grub.device = "/dev/vda";
  boot.initrd.availableKernelModules = [ "ata_piix" "uhci_hcd" "xen_blkfront" "vmw_pvscsi" ];
  boot.initrd.kernelModules = [ "nvme" ];

  # Workaround for https://github.com/NixOS/nix/issues/8502
  services.logrotate.checkConfig = false;

  zramSwap.enable = true;

  networking.networkmanager.enable = true;
  networking.hostName = "lebenshilfe-uslar";
  networking.domain = "de";

  fileSystems."/" = { device = "/dev/vda1"; fsType = "ext4"; };

  nix = {
    settings.trusted-users = [ "admin" ];
    extraOptions = ''
      experimental-features = nix-command flakes
    '';
  };
  
  services.openssh.enable = true;
  users.users.root.openssh.authorizedKeys.keys = [
    ''ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIM7SXkreRFT8Eb3+1WS+5Fz/5W2LuExLfsa7qFUS9k6Y autumnal@Mac-mini.local''
    ''ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILKYgRtPDT4v38pRxvOsCgI3l8f8Te14lFMdbWuM98KG autumnal@roxy''
    ''sk-ssh-ed25519@openssh.com AAAAGnNrLXNzaC1lZDI1NTE5QG9wZW5zc2guY29tAAAAID6cRpwV5pivNp8GWF3uAw4yOEJIYGkfMchIUeL+3f3hAAAACXNzaDp5azUuMQ== ssh:yk5.1''
  ];

  services.journald.extraConfig = "SystemMaxUse=250M";
  time.timeZone = "Europe/Berlin";
  i18n.defaultLocale = "en_GB.UTF-8";
  system.stateVersion = "23.11";
}
