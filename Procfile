release: python manage.py migrate --no-input
web: gunicorn config.wsgi --workers ${WEB_CONCURRENCY:-2} --timeout 60
