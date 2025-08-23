FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /tmp_app
COPY pyproject.toml uv.lock start.sh /tmp_app/
RUN uv sync
RUN chmod +x start.sh

# UID 1000のユーザー作成
RUN adduser -D -u 1000 user
USER 1000

CMD ["sh", "start.sh"]