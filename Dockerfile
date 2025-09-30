FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# install require
COPY requirements.txt .
RUN pip install -r requirements.txt

# COPY code
COPY . .

EXPOSE 8926

CMD ["gunicorn", "-w", "2", "-k", "gevent", "--timeout", "180", "-b", "0.0.0.0:8926", "app:app"]
