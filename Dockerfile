FROM python:3.12-slim-bookworm AS base

FROM base AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS deploy

COPY --from=build /usr/local /usr/local

WORKDIR /app
COPY . /app

ENV PYTHONPATH=/app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
