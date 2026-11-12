FROM golang:1.26.2-bookworm AS builder

WORKDIR /build

# hadolint ignore=DL3015
RUN apt-get update && \
    apt-get install -y \
        unzip \
        curl \
        zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

COPY go.mod go.sum ./
RUN go mod tidy

COPY install.sh ./
COPY . .

RUN mkdir -p /build/config/cookies && \
    chmod +x install.sh && \
    ./install.sh -n -t --quiet --skip-summary && \
    CGO_ENABLED=1 go build -v -trimpath -ldflags="-w -s" -o app ./cmd/app/


FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        unzip \
        ca-certificates \
        libssl3 \
        zlib1g && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /etc/ssl/certs /etc/ssl/certs

RUN curl -fL \
      https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux \
      -o /usr/local/bin/yt-dlp && \
    chmod 0755 /usr/local/bin/yt-dlp && \
    curl -fsSL https://deno.land/install.sh -o /tmp/deno-install.sh && \
    DENO_INSTALL=/usr/local sh /tmp/deno-install.sh -y --no-modify-path && \
    chmod 0755 /usr/local/bin/deno && \
    rm -f /tmp/deno-install.sh

ENV LD_LIBRARY_PATH=/app:$LD_LIBRARY_PATH
ENV TDJSON_PATH=/app/libtdjson.so.1.8.66

RUN useradd -r -u 10001 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app

COPY --from=builder /build/app /app/app
COPY --from=builder /build/libtdjson.so* /app/
COPY --from=builder /build/config/cookies /app/config/cookies
RUN chmod 0755 /app/libtdjson.so* && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["/app/app"]