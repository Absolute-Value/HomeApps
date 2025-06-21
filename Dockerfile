FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /tmp_app
COPY app/pyproject.toml app/uv.lock app/start.sh /tmp_app/
RUN uv sync

EXPOSE 8504
RUN chmod +x start.sh
CMD ["sh", "start.sh"]