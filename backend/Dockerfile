# Python 3.10 base image
FROM python:3.10-slim

# Install system dependencies (libgl1-mesa-dri: replacement for libgl1-mesa-glx on Debian 12+)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-dri \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Upgrade pip and install in two steps (if one fails, error is clearer)
RUN pip install --upgrade pip
# Step 1: lightweight deps (no heavy binaries)
RUN pip install --no-cache-dir --default-timeout=300 \
    "fastapi>=0.104.0" "uvicorn[standard]>=0.24.0" websockets "pydantic>=2.0.0" \
    "pydantic-settings>=2.0.0" python-multipart "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" python-dotenv "pandas>=2.0.0" openpyxl reportlab \
    "sqlalchemy>=2.0.0" "psycopg2-binary>=2.9.9" "pytest>=7.4.0"
# Step 2: numpy, opencv, ultralytics, matplotlib (heavier; if this fails, run build with --progress=plain to see pip error)
RUN pip install --no-cache-dir --default-timeout=300 \
    "numpy>=1.24.0,<2.0.0" "opencv-python-headless>=4.8.0" "ultralytics>=8.0.0" "matplotlib>=3.7.0"

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
