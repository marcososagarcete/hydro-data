FROM python:3.11.2-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the exact library versions you froze
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy code and small runtime dataset
COPY src/ /app/src/
COPY data/ /app/data/

# App configuration
ENV DATA_DIR=/app/data
ENV PORT=7860
EXPOSE 7860

WORKDIR /app/src
CMD ["python", "munimp.py"]
