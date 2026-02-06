FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2 \
    libpangocairo-1.0-0 \
    libffi-dev \
    shared-mime-info \
    gcc \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || \
    (echo "Some packages failed, installing core packages only..." && \
     pip install --no-cache-dir flask flask-login flask-sqlalchemy werkzeug gunicorn \
     Pillow img2pdf PyMuPDF pillow-heif pdf2docx markdown2 markdown python-docx \
     decorator pandas openpyxl requests holidays APScheduler yt-dlp imageio-ffmpeg numpy && \
     pip install --no-cache-dir moviepy || echo "moviepy failed" && \
     pip install --no-cache-dir xhtml2pdf || echo "xhtml2pdf failed" && \
     pip install --no-cache-dir cairosvg || echo "cairosvg failed" && \
     pip install --no-cache-dir python-whois || echo "python-whois failed" && \
     pip install --no-cache-dir opencv-python-headless || echo "opencv failed" && \
     pip install --no-cache-dir spacy || echo "spacy failed")

# Download spacy language model (optional, for name recognition)
RUN python -m spacy download de_core_news_sm || echo "Spacy model download skipped"

COPY . .

# Environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose port 5000
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]

