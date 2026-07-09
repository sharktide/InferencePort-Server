FROM python:3.13-slim
LABEL org.opencontainers.image.source=https://github.com/sharktide/InferencePort-Server

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

COPY --chown=user start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
