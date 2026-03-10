{ config, lib, pkgs, self, ... }:

with lib;

let
  cfg = config.services.lebenshilfe-cms;
in {
  options.services.lebenshilfe-cms = {
    enable = mkEnableOption "Lebenshilfe CMS Service";

    package = mkOption {
      type = types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.lebenshilfe-cms;
      description = "The Lebenshilfe CMS package to use.";
    };

    user = mkOption {
      type = types.str;
      default = "lebenshilfe";
      description = "User account under which the CMS runs.";
    };

    group = mkOption {
      type = types.str;
      default = "lebenshilfe";
      description = "Group under which the CMS runs.";
    };

    socketPath = mkOption {
      type = types.str;
      default = "/run/lebenshilfe-cms/gunicorn.sock";
      description = "Path to the Gunicorn Unix socket.";
    };

    dbHost = mkOption {
      type = types.str;
      default = "/run/postgresql";
      description = "The hostname, IP address, or directory containing the Unix domain socket of the database server.";
    };

    allowedHosts = mkOption {
      type = types.listOf types.str;
      default = [ "localhost" ];
      description = "List of host/domain names that this Django site can serve.";
    };

    environmentFile = mkOption {
      type = types.path;
      description = "Path to the environment file containing the SECRET_KEY.";
    };

    stateDir = mkOption {
      type = types.str;
      default = "/var/lib/lebenshilfe-cms";
      description = "Directory for persistent data (Static and Media).";
    };

    createWrapper = mkOption {
      type = types.bool;
      default = true;
      description = "Erstellt ein Wrapper-Skript im Systempfad, um manage.py mit dem korrekten Environment auszuführen.";
    };
  };

  config = mkIf cfg.enable {
    users.users.${cfg.user} = {
      isSystemUser = true;
      group = cfg.group;
    };
    users.groups.${cfg.group} = {};

    systemd.services.lebenshilfe-cms = {
      description = "Gunicorn instance to serve Lebenshilfe CMS";
      after = [ "network.target" "postgresql.service" ];
      wantedBy = [ "multi-user.target" ];
      
      preStart = ''
        ${cfg.package}/bin/lebenshilfe-manage migrate --noinput
        ${cfg.package}/bin/lebenshilfe-manage collectstatic --noinput
      '';

      serviceConfig = {
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.stateDir;
        EnvironmentFile = cfg.environmentFile;
        
        Environment = [
          "DEBUG=true"
          "STATIC_ROOT=${cfg.stateDir}/static"
          "MEDIA_ROOT=${cfg.stateDir}/media"
          "DATABASE_URL=postgres:///${cfg.user}?host=${cfg.dbHost}"
          "ALLOWED_HOSTS=${concatStringsSep "," cfg.allowedHosts}"
        ];

        RuntimeDirectory = "lebenshilfe-cms";
        StateDirectory = "lebenshilfe-cms";

        ExecStart = ''
          ${cfg.package}/bin/lebenshilfe-gunicorn \
            --workers 4 \
            --bind unix:${cfg.socketPath} \
            lebenshilfe.wsgi:application
        '';

        Restart = "always";
      };
    };
    environment.systemPackages = mkIf cfg.createWrapper [
      (pkgs.writeShellApplication {
        name = "lebenshilfe-manage";
        text = ''
          exec sudo -u ${cfg.user} bash -c '
            set -o allexport
            source "${cfg.environmentFile}"
            set +o allexport

            export STATIC_ROOT="${cfg.stateDir}/static"
            export MEDIA_ROOT="${cfg.stateDir}/media"
            export DATABASE_URL="postgres:///${cfg.user}?host=${cfg.dbHost}"
            export ALLOWED_HOSTS="${concatStringsSep "," cfg.allowedHosts}"

            cd "${cfg.stateDir}"
            exec ${cfg.package}/bin/lebenshilfe-manage "$@"
          ' _ "$@"
        '';
      })
    ];
  };
}
