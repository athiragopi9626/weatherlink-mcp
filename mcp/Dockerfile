FROM python:3.14-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency definitions
COPY pyproject.toml uv.lock ./

# Install locked dependencies
RUN uv sync --locked --no-dev --no-install-project

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "python", "weather.py"]