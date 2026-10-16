#!/usr/bin/env bash
# Build step for Render (and any host that runs a build script).
# The compiled Tailwind CSS is committed, so Node is not required here.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# First deploy only: load the résumé content. Safe to leave on — it does
# nothing once a profile exists — but switch it off after the first deploy.
if [ "${SEED_ON_DEPLOY:-0}" = "1" ]; then
  python manage.py seed_portfolio
fi
