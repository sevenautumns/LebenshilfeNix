{ pkgs, python3Packages }:

python3Packages.buildPythonPackage rec {
  pname = "django-unfold";
  version = "0.85.0";
  pyproject = true;

  src = pkgs.fetchFromGitHub {
    owner = "unfoldadmin";
    repo = pname;
    rev = version;
    sha256 = "sha256-5B/A02qGUMgkPOCdG0M9+upSrrplFOy1L4LnPjJDc/Y=";
  };

  build-system = with python3Packages; [
    hatchling
  ];

  propagatedBuildInputs = with python3Packages; [
    django
  ];

  pythonImportsCheck = [ "unfold" ];
}
