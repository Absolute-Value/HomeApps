FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app
COPY app/pyproject.toml app/uv.lock /app/
RUN uv sync

COPY app/ /app
EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8504", "--server.address=0.0.0.0"]