{ pkgs, ... }:
let
  python = pkgs.python3.override {
    packageOverrides = self: super: {
      python-lsp-server = (super.python-lsp-server.override {
        withAutopep8 = false;
        withYapf = false;
        withPylint = false;
        withPycodestyle = false;
        withFlake8 = false;
      }).overridePythonAttrs { doCheck = false; };
      pylsp-mypy = super.pylsp-mypy.overridePythonAttrs (oldAttrs: {
        propagatedBuildInputs = oldAttrs.propagatedBuildInputs ++ [ self.toml ];
      });
    };
  };
  pylspWithPlugins = ps:
    with ps; [
      python-lsp-server
      pylsp-mypy
      python-lsp-black
      pyls-isort
    ];
  pythonEnv = python.withPackages
    (ps: [ ps.antlr4-python3-runtime ps.llvmlite ] ++ pylspWithPlugins ps);
in
{
  devshell.name = "bkit";
  devshell.packages = with pkgs; [ antlr jasmin openjdk_headless pythonEnv ];
}
