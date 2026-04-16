{
  pkgs,
  python3Packages,
  django-unfold,
}:

python3Packages.buildPythonApplication rec {
  pname = "lebenshilfe-cms";
  version = "1.0.0";
  pyproject = true;

  src = ./.;

  nativeBuildInputs = [
    python3Packages.setuptools
    python3Packages.wheel
    pkgs.makeWrapper
    pkgs.gettext
  ];

  propagatedBuildInputs = with python3Packages; [
    django
    django-environ
    psycopg
    dj-database-url
    django-unfold
    django-allauth
    requests
    gunicorn
    weasyprint
    model-bakery
    pytest
    pytest-django
    pytest-xdist
  ];

  nativeCheckInputs = with python3Packages; [
    pytestCheckHook
  ];

  preCheck = ''
    export SECRET_KEY="temporary-secret-key-for-nix-build"
    export DATABASE_URL="sqlite:///:memory:"
  '';

  preBuild = "${python3Packages.python.interpreter} -m django compilemessages";

  postInstall = ''
    LIB_DIR=$out/${python3Packages.python.sitePackages}
    cp manage.py $LIB_DIR/
    cp -r static $LIB_DIR/
    cp -r templates $LIB_DIR/
    cp -r locale $LIB_DIR/

    makeWrapper ${python3Packages.python.interpreter} $out/bin/lebenshilfe-manage \
      --add-flags "$LIB_DIR/manage.py" \
      --prefix PYTHONPATH : "$LIB_DIR:$PYTHONPATH"

    makeWrapper ${python3Packages.gunicorn}/bin/gunicorn $out/bin/lebenshilfe-gunicorn \
      --prefix PYTHONPATH : "$LIB_DIR:$PYTHONPATH" \
      --append-flag lebenshilfe.wsgi:application
      
    mkdir -p $out/share/doc/${pname}
    cp ${../../NOTICE} $out/share/doc/${pname}/NOTICE
  '';
}
