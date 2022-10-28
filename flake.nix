{
  inputs.nixpkgs.url = "local";

  outputs = { self, nixpkgs }:
    nixpkgs.lib.flake.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.devshell.mkShell ./devshell.nix;
        packages.libbkit = pkgs.stdenv.mkDerivation {
          name = "libbkit";
          src = ./lib;

          makeFlags = [ "PREFIX=$(out)" ];
          buildFlags = [ "libbkit" ];
        };
      });
}
