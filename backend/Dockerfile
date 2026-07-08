FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for compiling packages if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-create the HuggingFace cache dir so the local neural models
# can be downloaded into it on first boot.
RUN mkdir -p /root/.cache/huggingface


# Copy source code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
