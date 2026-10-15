#!/bin/sh
# Re-apply the Wyoming assist_satellite audio-forwarding race fix.
#
# Home Assistant drops microphone audio coming from a satellite when a new
# pipeline starts while the previous one is still winding down: the old run's
# "run-end" clears _is_pipeline_running *after* the new run set it, so every
# subsequent AudioChunk is treated as unexpected and discarded and the new run
# waits forever (satellite stuck in "listening").
#
# This hook is idempotent and is meant to run at boot after Docker. It does
# nothing if the container is absent/stopped or already patched.
set -eu

CONTAINER=homeassistant

command -v docker >/dev/null 2>&1 || exit 0
docker inspect "$CONTAINER" >/dev/null 2>&1 || exit 0
[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" = "true" ] || exit 0

RESULT=$(docker exec -i "$CONTAINER" python3 - <<'PY'
p = "/usr/src/homeassistant/homeassistant/components/wyoming/assist_satellite.py"
try:
    s = open(p).read()
except OSError:
    print("missing")
    raise SystemExit(0)

old = """                elif AudioChunk.is_type(client_event.type) and (
                    self._is_pipeline_running or (wake_word_phrase is not None)
                ):
                    if not self._is_pipeline_running:"""
new = """                elif AudioChunk.is_type(client_event.type) and (
                    self._is_pipeline_running
                    or (wake_word_phrase is not None)
                    or (self._pipeline_task is not None)
                ):
                    if (not self._is_pipeline_running) and (
                        self._pipeline_task is None
                    ):"""

if new in s:
    print("already")
elif old in s:
    open(p, "w").write(s.replace(old, new))
    print("patched")
else:
    print("nomatch")
PY
)

case "$RESULT" in
    patched)
        logger -t patch-ha-wyoming "applied fix; restarting $CONTAINER"
        docker restart "$CONTAINER" >/dev/null
        ;;
    nomatch)
        logger -t patch-ha-wyoming "pattern not found (HA version changed?); skipped"
        ;;
esac
