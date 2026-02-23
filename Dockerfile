FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for GDAL
RUN apt-get update && apt-get install -y gdal-bin libgdal-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY fastapi_app ./fastapi_app

# Expose port
EXPOSE 8000

# Command to run the FastAPI app
CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
