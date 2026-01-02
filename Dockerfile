
# 1. Base image with Python 3.10 (slim version for smaller size)
FROM python:3.10-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# 3. Install system dependencies for OpenCV and other tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 4. Set working directory
WORKDIR /app

# 5. Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the application code
COPY . .

# 7. Create necessary directories for operation
RUN mkdir -p uploads results

# 8. Establish a non-root user (Heroku security best practice)
RUN useradd -m myuser
RUN chown -R myuser:myuser /app
USER myuser

# 9. Expose port (Heroku sets $PORT dynamically, but this is good documentation)
EXPOSE $PORT

# 10. Command to run the application using uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
