# Satellite image

This directory contains a small `Dockerfile` that builds the **upstream**
[`rhasspy/wyoming-satellite`](https://github.com/rhasspy/wyoming-satellite)
voice satellite, with one addition: `alsa-utils` (so the image has
`arecord`/`aplay` for a plain USB microphone + speaker, without the separate
external mic/snd containers).

The upstream source is **cloned at build time** and pinned to a specific commit
(`SATELLITE_REF`) rather than vendored into this repo, so this project stays
MIT-licensed while the satellite keeps its own upstream license.

## Build

```bash
docker compose build satellite
```

The compose file tags it `rhasspy/wyoming-satellite:1.4.1` (matching the upstream
release this commit corresponds to). Override the pin with:

```bash
docker compose build --build-arg SATELLITE_REF=<commit-sha> satellite
```

## Running

The compose service passes:

- `--mic-command` / `--snd-command`: raw ALSA commands for your microphone and
  speaker. Find the right device numbers with `arecord -l` and `aplay -l`
  (e.g. `plughw:3,0` = a USB headset mic, `plughw:2,0` = the 3.5 mm jack).
- `--wake-uri` / `--wake-word-name`: the wake-word service (port 10400) and the
  model name.
- `--zeroconf-host 127.0.0.1`: makes Home Assistant auto-discover the satellite.

## Notes

- The satellite does the wake-word detection **on-device** (it streams mic audio
  to the wake service and reports detections to Home Assistant).
- Continued conversation (answering a follow-up without repeating the wake word)
  is **not** supported by this satellite; Home Assistant re-arms the wake word
  after each turn. See `docs/troubleshooting.md`.
