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

  propagatedBuildInputs = with python3Packages; [
    py-moneyed
    django
  ];

  nativeCheckInputs = with python3Packages; [
    pytestCheckHook
    pytest-cov
    certifi
    pytest-django
  ];

  pytestFlagsArray = [
    "-k 'not test_mixer_blend'"
  ];

  pythonImportsCheck = [ "djmoney" ];
}
