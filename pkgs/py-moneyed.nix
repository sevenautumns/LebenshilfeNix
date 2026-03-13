{ pkgs, python3Packages }:

python3Packages.buildPythonPackage rec {
  pname = "py-moneyed";
  version = "3.0";
  pyproject = true;

  src = pkgs.fetchFromGitHub {
    owner = "py-moneyed";
    repo = pname;
    rev = "v${version}";
    sha256 = "sha256-k0ZbLwog6TYxKDLZV7eH1Br8buMPfpOkgp+pMN/qdB8=";
  };

  build-system = with python3Packages; [
    setuptools
  ];

  nativeCheckInputs = with python3Packages; [
    babel
    typing-extensions
  ];

  pythonImportsCheck = [ "moneyed" ];

  doCheck = true;
}
