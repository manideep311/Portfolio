# Portable image for Fly.io, Railway, a VPS, or anywhere that runs containers.

# 1) Build the Tailwind stylesheet from the templates
FROM node:22-slim AS css
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY assets ./assets
COPY templates ./templates
COPY portfolio/templates ./portfolio/templates
COPY portfolio/templatetags ./portfolio/templatetags
COPY static/js ./static/js
RUN npm run build:css

# 2) Python runtime
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
COPY --from=css /app/static/css/app.css static/css/app.css
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --no-input

RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --no-input && gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout 60"]
