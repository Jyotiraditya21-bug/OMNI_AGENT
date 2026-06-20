FROM python:3.11-slim

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy project specification files
COPY pyproject.toml .

# Sync dependencies using uv
RUN uv sync --frozen

# Copy source directories
COPY . .

# Expose backend port
EXPOSE 8000

# Execute server
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
