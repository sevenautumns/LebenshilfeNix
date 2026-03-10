{ pkgs, python3Packages }:

python3Packages.buildPythonPackage rec {
  pname = "django-unfold";
  version = "0.83.1";
  pyproject = true;

  src = pkgs.fetchFromGitHub {
    owner = "unfoldadmin";
    repo = pname;
    rev = version;
    sha256 = "sha256-hWN3g+dDAW5lsYiKZNxY+ERjSeexHkRV4HjCESrmgU0=";
  };

  nativeBuildInputs = with python3Packages; [
    hatchling
  ];

  nativeCheckInputs = with python3Packages; [
    pytest
    pytest-django
  ];

  pythonImportsCheck = [ "unfold" ];

  doCheck = true;
}
