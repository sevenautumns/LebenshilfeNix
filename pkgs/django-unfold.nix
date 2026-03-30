{ pkgs, python3Packages }:

python3Packages.buildPythonPackage rec {
  pname = "django-unfold";
  version = "0.87.0";
  pyproject = true;

  src = pkgs.fetchFromGitHub {
    owner = "unfoldadmin";
    repo = pname;
    rev = version;
    sha256 = "sha256-C/o8w3nrJeMKW0s8mYnP3vjoDEVpm1fg8Wv2Egsj7gk=";
  };

  build-system = with python3Packages; [
    hatchling
  ];

  propagatedBuildInputs = with python3Packages; [
    django
  ];

  pythonImportsCheck = [ "unfold" ];
}
