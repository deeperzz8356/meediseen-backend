FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from the backend requirements file.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the backend app and the shared model package used by the pipeline.
COPY backend ./backend
COPY model ./model
COPY uploads ./uploads

# Set environment defaults.
ENV PORT=10000
ENV APP_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 10000

# Render provides PORT at runtime; fall back to 10000 locally.
CMD ["sh", "-lc", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
