FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.7.14 /uv /uvx /bin/

ENV UV_SYSTEM_PYTHON=1

COPY . /app

WORKDIR /app
RUN uv export --no-hashes --format requirements-txt > requirements.txt
RUN uv pip install -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--forwarded-allow-ips=*"]
