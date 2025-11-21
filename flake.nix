{
  description = "Bare python dev env";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";

    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    flake-utils,
    nixpkgs,
  } @ inputs:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = inputs.nixpkgs.legacyPackages.${system};
    in {
      devShells.default = pkgs.mkShell {
        packages = with pkgs; [
          pkg-config
          (python313.withPackages (python-pkgs: with python-pkgs; [
          basedpyright
          pillow
          numpy
          pip
          tkinter
          ]))
        ];
      };
    });
}
