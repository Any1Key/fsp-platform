FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.lock ./
RUN pip install --no-cache-dir --requirement requirements.lock
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
