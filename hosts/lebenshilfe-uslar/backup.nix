
{ self, pkgs, config, ... }:
{
  age.secrets = {
    nextcloud-backup-pj92-env = {
      file = "${self}/secrets/nextcloud-backup-pj92-env.age";
      mode = "700";
      owner = "nextcloud";
    };
    nextcloud-backup-pj92-encryption = {
      file = "${self}/secrets/nextcloud-backup-pj92-encryption.age";
      mode = "700";
      owner = "nextcloud";
    };
  };
  
  services.restic.backups.nextcloud-backup = {
    repository = "s3:https://s3.eu-central-3.ionoscloud.com/nextcloud-backup-pj92";

    passwordFile = config.age.secrets.nextcloud-backup-pj92-encryption.path;
    environmentFile = config.age.secrets.nextcloud-backup-pj92-env.path;

    paths = [
      "/var/lib/nextcloud/data/__groupfolders/1/files"
      "/var/lib/nextcloud/data/__groupfolders/2/files"
      "/var/lib/nextcloud/data/__groupfolders/3/files"
    ];

    pruneOpts = [
      "--keep-daily 7"
      "--keep-weekly 5"
      "--keep-monthly 12"
      "--keep-yearly 10"
    ];

    timerConfig = {
      OnCalendar = "03:00";
      Persistent = true;
    };
  };
}
