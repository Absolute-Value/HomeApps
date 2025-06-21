FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app
COPY app/pyproject.toml app/uv.lock /app/
RUN uv sync

COPY app/ /app
EXPOSE 8504

RUN chmod +x start.sh
CMD ["sh", "start.sh"]