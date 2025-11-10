FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_PREFER_SYSTEM=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN UV_LINK_MODE=copy uv sync --frozen --no-dev

EXPOSE 8080

CMD ["uv", "run", "fitfile-customgpt-action", "--host", "0.0.0.0", "--port", "8080"]
