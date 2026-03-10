{ pkgs, config, ... }:
{
  environment.systemPackages = with pkgs; [
    dust
    btop
    helix
  ];
}
