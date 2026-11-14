FROM python:3.14-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project

COPY . .

EXPOSE 8080

CMD ["uv", "run", "--no-sync", "python", "-m", "agent.runtime"]