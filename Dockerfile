# Imagen del proyecto Django (servicio "web" de docker-compose.yml)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Librerías del sistema que necesita mysqlclient para compilarse
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# En tu Mac, docker-compose.yml usa runserver; esta línea es la de producción (Azure)
CMD ["sh", "startup.sh"]
