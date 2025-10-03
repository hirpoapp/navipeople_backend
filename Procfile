release: python manage.py makemigrations && python manage.py migrate
web: gunicorn settings.wsgi:application --log-file -