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
  ];

  postInstall = ''
    LIB_DIR=$out/${python3Packages.python.sitePackages}
    cp manage.py $LIB_DIR/
    cp -r static $LIB_DIR/
    cp -r templates $LIB_DIR/

    makeWrapper ${python3Packages.python.interpreter} $out/bin/lebenshilfe-manage \
      --add-flags "$LIB_DIR/manage.py" \
      --prefix PYTHONPATH : "$LIB_DIR:$PYTHONPATH"

    makeWrapper ${python3Packages.gunicorn}/bin/gunicorn $out/bin/lebenshilfe-gunicorn \
      --prefix PYTHONPATH : "$LIB_DIR:$PYTHONPATH"
      
    mkdir -p $out/share/doc/${pname}
    cp ${../../NOTICE} $out/share/doc/${pname}/NOTICE
  '';

  doCheck = false;
}
