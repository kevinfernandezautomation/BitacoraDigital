FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends openssl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh","-c","python manage.py makemigrations core && python manage.py migrate && python manage.py install_guards && python manage.py runserver 0.0.0.0:8000"]
