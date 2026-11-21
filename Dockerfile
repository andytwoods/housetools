FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app
COPY requirements ./requirements
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .

# Production settings so whitenoise's manifest storage is the one that runs.
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=sqlite:////tmp/build.db \
    NEXTDNS_PROFILE_ID=build-only NEXTDNS_API_TOKEN=build-only VOICE_MONKEY_TOKEN=build-only \
    python manage.py collectstatic --noinput \
    && rm -f /tmp/build.db

# Don't run the app as root.
RUN useradd --system --no-create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["sh", "run.sh"]
