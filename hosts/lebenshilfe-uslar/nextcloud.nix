{ self, pkgs, config, ... }:
{
  age.secrets = {
    nextcloud-secret = {
      file = "${self}/secrets/nextcloud-secret.age";
      mode = "700";
      owner = "nextcloud";
    };
  };

  services.nextcloud = {                
    enable = true;                   
    package = pkgs.nextcloud33;
    hostName = "nextcloud.lebenshilfe-uslar.de";
    https = true;
    database.createLocally = true;
    secretFile = config.age.secrets.nextcloud-secret.path;
    config = {
      dbtype = "pgsql";
      adminpassFile = null;
      adminuser = null;
    };
    settings = {
      maintenance_window_start = 4;
      mail_smtpmode = "smtp";
      mail_smtphost = "smtp.ionos.de";
      mail_smtpport = 587;
      mail_smtpsecure = "";
      mail_smtpauth = true;
      mail_from_address = "nicht-antworten";
      mail_domain = "lebenshilfe-uslar.de";
      mail_smtpname = "nicht-antworten@lebenshilfe-uslar.de";
    };
    phpOptions = {
      "opcache.interned_strings_buffer" = "32";
    };
    extraApps = {
      inherit (pkgs.nextcloud33Packages.apps) groupfolders;
    };
  };

  services.nginx.virtualHosts.${config.services.nextcloud.hostName} = {
    forceSSL = true;
    enableACME = true;
  };
}
