{
  pkgs,
  python3Packages,
  py-moneyed,
}:

python3Packages.buildPythonPackage rec {
  pname = "django-money";
  version = "3.6.0";
  pyproject = true;

  src = pkgs.fetchFromGitHub {
    owner = "django-money";
    repo = pname;
    rev = version;
    sha256 = "sha256-VxAKTtrbDMRhiLxqjVYt7pLGl0sy9F1iwswP/hxQ01k=";
  };

  build-system = with python3Packages; [
    setuptools
  ];

  nativeCheckInputs = with python3Packages; [
    py-moneyed
    pytest-django
  ];

  pythonImportsCheck = [ "djmoney" ];

  doCheck = true;
}
