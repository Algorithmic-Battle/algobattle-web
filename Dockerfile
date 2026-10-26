FROM python:3.14 AS api_builder
WORKDIR /code
COPY backend .
RUN pip install .
COPY docker/algobattle_version.py /code/algobattle_version.py
ARG ALGOBATTLE_DB_PW
ARG ALGOBATTLE_BASE_URL
ENV ALGOBATTLE_DB_PW=${ALGOBATTLE_DB_PW} ALGOBATTLE_BASE_URL=${ALGOBATTLE_BASE_URL}
RUN algobattle_api > openapi.json
RUN python -m algobattle_version installed > algobattle_version.txt

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS docs_builder
RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /code/algobattle
ADD "https://api.github.com/repos/Algorithmic-Battle/algobattle/commits/release?per_page=1" latest_commit
RUN git clone --depth 1 --branch release https://github.com/Algorithmic-Battle/algobattle.git .
COPY --from=api_builder /code/algobattle_version.txt /tmp/algobattle_version.txt
COPY docker/algobattle_version.py .
RUN python -m algobattle_version check /tmp/algobattle_version.txt
RUN uv sync --locked --group dev
RUN uv run --no-sync mkdocs build --site-dir /site

FROM node:26 AS frontend_builder
WORKDIR /code
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/env.d.ts frontend/index.html frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts ./
COPY --from=api_builder /code/openapi.json openapi.json
COPY frontend/public public/
COPY frontend/src src/
ARG ALGOBATTLE_BASE_URL
ENV ALGOBATTLE_BASE_URL=${ALGOBATTLE_BASE_URL}
RUN npm run build

FROM nginx
WORKDIR /code
COPY --from=api_builder /code/algobattle_version.txt algobattle_version.txt
COPY --from=docs_builder /site docs
COPY --from=frontend_builder /code/dist frontend
COPY nginx.conf /etc/nginx/nginx.conf
