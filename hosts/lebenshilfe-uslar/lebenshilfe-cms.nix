{ self, config, ... }: {
  age.secrets = {
    lebenshilfe-cms-secret = {
      file = "${self}/secrets/lebenshilfe-cms-secret.age";
      mode = "700";
      owner = config.services.lebenshilfe-cms.user;
    };
  };

  services.lebenshilfe-cms = {
    enable = true;
    allowedHosts = [ "dev.lebenshilfe-uslar.de" ];
    environmentFile = config.age.secrets.lebenshilfe-cms-secret.path; 
  };

  services.postgresql = {
    ensureDatabases = [ 
      config.services.lebenshilfe-cms.user 
    ];
    ensureUsers = [
      {
        name = config.services.lebenshilfe-cms.user;
        ensureDBOwnership = true;
      }
    ];
  };

  services.nginx = {
    enable = true;
    virtualHosts."dev.lebenshilfe-uslar.de" = {
      forceSSL = true;
      enableACME = true;

      locations."/" = {
        proxyPass = "http://unix:${config.services.lebenshilfe-cms.socketPath}";
        extraConfig = ''
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
        '';
      };

      locations."/static/" = {
        alias = "/var/lib/lebenshilfe-cms/static/";
      };
    };
  };
}
