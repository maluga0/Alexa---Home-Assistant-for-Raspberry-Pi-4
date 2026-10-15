FROM rhasspy/wyoming-openwakeword:latest

# The bundled (older) wyoming in this image can advertise over zeroconf, but
# the optional `zeroconf` dependency is not installed. Add it so Home Assistant
# can auto-discover the wake-word service like the other Wyoming services.
RUN /usr/src/.venv/bin/pip install --no-cache-dir zeroconf
