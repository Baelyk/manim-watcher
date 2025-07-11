{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs {inherit system;};
    pythonPackages = ps:
      with ps; [
        mpv
        watchfiles
      ];
    pythonEnv = pkgs.python3.withPackages pythonPackages;
    buildInputs = with pkgs; [
      # Python and packages
      pythonEnv
      # MPV for the watcher
      mpv
    ];
  in {
    packages.${system}.default = pkgs.stdenv.mkDerivation {
      name = "manim-watcher";
      propagatedBuildInputs = buildInputs;
      dontUnpack = true;
      installPhase = "install -Dm755 ${./main.py} $out/bin/manim-watcher";
    };

    devShells.${system}.default = pkgs.mkShell {
      buildInputs = with pkgs;
        [
          pyright
          black
        ]
        ++ buildInputs;

      shellHook = ''
        echo $(python3 --version)
      '';
    };
  };
}
