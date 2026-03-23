{ pkgs, python3Packages }:

python3Packages.buildPythonPackage rec {
  pname = "django-unfold";
  version = "0.86.1";
  pyproject = true;

  src = pkgs.fetchFromGitHub {
    owner = "unfoldadmin";
    repo = pname;
    rev = version;
    sha256 = "sha256-T7v5ov6wSSqD5iowGO2EjAvg5Goda0q+qqImvRwolaU=";
  };

  build-system = with python3Packages; [
    hatchling
  ];

  propagatedBuildInputs = with python3Packages; [
    django
  ];

  pythonImportsCheck = [ "unfold" ];
}
