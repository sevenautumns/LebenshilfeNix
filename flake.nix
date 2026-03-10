{
  description = "Lebenshilfe Server Configuration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";

    agenix = {
      url = "github:ryantm/agenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      nixpkgs,
      agenix,
      ...
    }@inputs:
    let
      lib = nixpkgs.lib;
      pkgs = import nixpkgs {
        system = "x86_64-linux";
      };
    in
    {
      nixosConfigurations.lebenshilfe-uslar = lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          { networking.hostName = "lebenshilfe-uslar"; }
          agenix.nixosModules.default
          ./server.nix
        ];
        specialArgs = {
          inherit inputs;
          flakeRoot = ./.;
        };
      };
    };
}
