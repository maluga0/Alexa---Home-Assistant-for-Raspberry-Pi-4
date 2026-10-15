FROM python:3.11-slim-bookworm

ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

# avahi-utils : mDNS / zeroconf tooling (Home Assistant discovery)
# alsa-utils  : arecord / aplay for the microphone and speaker
# git         : to fetch the upstream source at build time
RUN apt-get update && \
    apt-get install --yes --no-install-recommends avahi-utils alsa-utils git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build the upstream Wyoming satellite at a pinned commit.
# The source is fetched at build time (not vendored here) so this repo stays
# MIT while the satellite keeps its own upstream license.
ARG SATELLITE_REF=7a3ba2bc23fc6699adae4f5bbac4ce529fe2a623
RUN git clone https://github.com/rhasspy/wyoming-satellite.git . && \
    git checkout "${SATELLITE_REF}" && \
    rm -rf .git

RUN chmod +x script/setup script/run docker/run && \
    script/setup && \
    cp docker/run ./run

EXPOSE 10700
ENTRYPOINT ["/app/run"]
