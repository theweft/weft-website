{
  description = "weft-website: development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.just
            # Local preview and deploys (Cloudflare Workers).
            pkgs.wrangler
            # Link check, spelling, licences.
            pkgs.lychee
            pkgs.typos
            pkgs.reuse
            pkgs.python3
          ];
        };
      });
    };
}
