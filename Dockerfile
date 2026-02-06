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
    pip install --no-cache-dir -r requirements.txt

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

