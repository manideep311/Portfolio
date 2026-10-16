#!/usr/bin/env bash
# One-time setup on PythonAnywhere (free plan). From a PythonAnywhere Bash console:
#
#   git clone https://github.com/manideep311/Portfolio.git
#   bash ~/Portfolio/deploy/pythonanywhere_setup.sh
#
# It creates the virtualenv, installs dependencies, writes .env (only if missing),
# sets up the database, loads the résumé content and collects static files.
# At the end it prints exactly what to enter on the PythonAnywhere "Web" tab.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PA_USER="${PA_USER:-$USER}"
DOMAIN="${PA_DOMAIN:-$PA_USER.pythonanywhere.com}"
VENV="${VENV:-$HOME/.virtualenvs/portfolio}"

# Newest available Python 3.10+ (Django 5.2 needs 3.10 or later)
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
  for version in 3.13 3.12 3.11 3.10; do
    if command -v "python$version" >/dev/null 2>&1; then
      PYTHON="python$version"
      break
    fi
  done
fi
if [ -z "$PYTHON" ]; then
  echo "Could not find Python 3.10 or newer." >&2
  exit 1
fi
PY_VERSION="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

echo "==> Python $PY_VERSION, virtualenv at $VENV"
if [ ! -d "$VENV" ]; then
  "$PYTHON" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet --no-cache-dir --upgrade pip
pip install --quiet --no-cache-dir -r "$PROJECT_DIR/requirements-pythonanywhere.txt"

cd "$PROJECT_DIR"
if [ ! -f .env ]; then
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
  cat > .env <<EOF
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=$SECRET_KEY
DJANGO_ALLOWED_HOSTS=$DOMAIN
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMAIN
SITE_URL=https://$DOMAIN
# PythonAnywhere's "Force HTTPS" setting does the redirect
DJANGO_SECURE_SSL_REDIRECT=0
EOF
  chmod 600 .env
  echo "==> Wrote .env for $DOMAIN"
else
  echo "==> Keeping your existing .env"
fi

echo "==> Setting up the database"
python manage.py migrate --no-input
python manage.py seed_portfolio
echo "==> Collecting static files"
python manage.py collectstatic --no-input --verbosity 0

cat <<EOF

============================================================
 Setup finished. Two things left:

 1. Create your CMS login (run now, in this console):

      source $VENV/bin/activate && cd $PROJECT_DIR && python manage.py createsuperuser

 2. On the Web tab: "Add a new web app" -> Manual configuration -> Python $PY_VERSION
    Then fill in:

      Source code:        $PROJECT_DIR
      Working directory:  $PROJECT_DIR
      Virtualenv:         $VENV

      Static files:
        URL /static/   ->  Directory $PROJECT_DIR/staticfiles
        URL /media/    ->  Directory $PROJECT_DIR/media

      Security:           Force HTTPS = Enabled

    Open the "WSGI configuration file" link, replace everything with
    these three lines, save, then press the green Reload button:

      import sys
      sys.path.insert(0, "$PROJECT_DIR")
      from config.wsgi import application  # noqa

 Your site: https://$DOMAIN
 Your CMS:  https://$DOMAIN/admin/
============================================================
EOF
