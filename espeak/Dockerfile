FROM python:3.11-slim-bookworm

ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --yes --no-install-recommends espeak-ng && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir wyoming zeroconf

WORKDIR /app
COPY espeak_server.py ./

EXPOSE 10500
ENTRYPOINT ["python3", "/app/espeak_server.py"]
