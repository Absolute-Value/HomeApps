FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /tmp_app
RUN uv init
RUN uv add streamlit

# UID 1000のユーザー作成
RUN adduser -D -u 1000 user
USER 1000

CMD ["uv", "run", "--", "streamlit", "run", "app.py", "--server.enableCORS=false", "--server.enableXsrfProtection=false", "--server.headless=true"]
