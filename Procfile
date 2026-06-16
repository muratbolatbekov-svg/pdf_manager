web: python manage.py migrate --noinput && python manage.py bootstrap_admin && gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --log-file -
