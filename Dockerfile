FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PORT=8000
CMD python -m quakewatch.db && gunicorn --workers 1 --threads 4 --bind 0.0.0.0:$PORT "quakewatch.app:create_app()"
