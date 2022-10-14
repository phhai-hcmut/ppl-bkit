{
  inputs.nixpkgs.url = "local";

  outputs = { self, nixpkgs }:
    nixpkgs.lib.flake.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in { devShells.default = pkgs.devshell.mkShell ./devshell.nix; });
}
