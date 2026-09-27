web: gunicorn prism.wsgi --bind 0.0.0.0:$PORT
worker: celery -A prism worker -l info
release: python manage.py migrate
