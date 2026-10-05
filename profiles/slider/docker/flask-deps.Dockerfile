FROM --platform=linux/amd64 python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev libpcre2-dev libpq-dev build-essential git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# upstream patch: SQLAlchemy conflict (same as compose/Dockerfile.flask)
RUN grep -q '^SQLAlchemy==2.0.31' requirements.txt \
        || (echo "ERROR: SQLAlchemy==2.0.31 not found" && exit 1) && \
    sed -i 's/^SQLAlchemy==2.0.31$/SQLAlchemy>=2.0.36,<2.1.0/' requirements.txt && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir \
        gigachain gigachat gigachain-cli \
        'flask-openapi3[swagger,redoc,rapidoc,rapipdf,scalar,elements]' \
        redis

RUN (gigachain install-rus-certs || true)
