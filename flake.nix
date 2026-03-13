{
  description = "Lebenshilfe Server Configuration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    flake-utils.url = "github:numtide/flake-utils";
    agenix = {
      url = "github:ryantm/agenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      agenix,
      ...
    }@inputs:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        packages = rec {
          django-unfold = pkgs.callPackage ./pkgs/django-unfold.nix { };
          # FIXME: use 26.05 py-moneyed
          py-moneyed = pkgs.callPackage ./pkgs/py-moneyed.nix { };

          django-money = pkgs.callPackage ./pkgs/django-money.nix {
            inherit py-moneyed;
          };

          lebenshilfe-cms = pkgs.callPackage ./apps/lebenshilfe-cms/default.nix {
            inherit django-unfold django-money;
          };
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages."${system}".lebenshilfe-cms ];
          buildInputs = [
            agenix.packages.${system}.default
            pkgs.nixos-rebuild-ng
          ];

          shellHook = ''
            export DEBUG=True
            export SECRET_KEY='django-insecure-dev-only'
            export DATABASE_URL="sqlite:///$(pwd)/db.sqlite3"

            # # Optional: tell Django where to put collected assets locally
            # export STATIC_ROOT="$(pwd)/staticfiles"
          '';
        };
      }
    )
    // {
      nixosModules.lebenshilfe-cms = import ./modules/lebenshilfe-cms.nix;

      nixosConfigurations.lebenshilfe-uslar = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        specialArgs = { inherit self inputs; };
        modules = [
          ./hosts/lebenshilfe-uslar/configuration.nix
          self.nixosModules.lebenshilfe-cms
          agenix.nixosModules.default
        ];
      };
    };
}
