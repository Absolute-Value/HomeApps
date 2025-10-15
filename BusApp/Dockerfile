FROM ghcr.io/astral-sh/uv:python3.13-alpine

# UID 1000のユーザー作成
RUN adduser -D -u 1000 user
USER 1000

CMD ["uv", "run", "app.py"]