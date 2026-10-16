#!/usr/bin/env bash
# Pull the latest code from GitHub and reload the site on PythonAnywhere:
#
#   bash ~/Portfolio/deploy/pythonanywhere_update.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PA_USER="${PA_USER:-$USER}"
VENV="${VENV:-$HOME/.virtualenvs/portfolio}"
WSGI_FILE="/var/www/${PA_USER//./_}_pythonanywhere_com_wsgi.py"

cd "$PROJECT_DIR"
echo "==> Pulling the latest code"
git pull --ff-only

# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet --no-cache-dir -r requirements-pythonanywhere.txt

echo "==> Applying database changes and static files"
python manage.py migrate --no-input
python manage.py collectstatic --no-input --verbosity 0

if [ -f "$WSGI_FILE" ]; then
  touch "$WSGI_FILE"   # PythonAnywhere reloads the site when this file changes
  echo "==> Reloaded https://${PA_USER}.pythonanywhere.com"
else
  echo "==> Done. Press Reload on the Web tab to see the changes."
fi
