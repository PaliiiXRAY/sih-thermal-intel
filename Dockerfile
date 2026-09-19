# Production / Demo Dockerfile for FireSense (SIH26162)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for geospatial packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY . .

# Environment Defaults
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run FastAPI via uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
