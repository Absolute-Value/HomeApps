FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /tmp_app
COPY pyproject.toml uv.lock /tmp_app/
RUN uv sync

CMD ["uv", "run", "--", "streamlit", "run", "app.py", "--server.enableCORS=false", "--server.enableXsrfProtection=false", "--server.headless=true"]
