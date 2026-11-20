FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg is needed for voice chat streaming AND for the animated welcome card
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    npm \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/

# install python packages first (better build cache)
COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app/

CMD ["bash", "start"]

