# Alexa-style voice assistant for Raspberry Pi 4 + Home Assistant

A fully local, private voice assistant for a **Home Assistant Container** install,
running on a **Raspberry Pi 4**: say *"Alexa, …"*, and Home Assistant answers
through a speaker — with sub-2-second responses.

Speech-to-text, text-to-speech and wake-word detection all run **on the Pi**
(Docker containers). The only optional external piece is the language model,
which can be any Home Assistant conversation agent (here: a cloud model via
Ollama, but a local model works too).

```
        "Alexa, turn on the kitchen light"
                   │
   ┌───────────────▼────────────────┐        ┌───────────────────────────┐
   │  wyoming-satellite (Pi)        │        │  Home Assistant (Container)│
   │  USB mic  ──► on-device wake    │  TCP   │  Assist pipeline            │
   │             (openWakeWord)     ├───────►│  1) STT  (sherpa/whisper)   │
   │  headphones ◄── TTS playback   │        │  2) LLM  (conversation)     │
   └────────────────────────────────┘        │  3) TTS  (espeak/piper)     │
                                             └───────────────────────────┘
```

## Why this repository

There is no single "install" for this on a Container install, and the pieces
that make it *fast on a Pi 4* are easy to get wrong. This repo collects a working
setup, including the two problems that cost the most time to find:

1. **TTS on a Pi 4 is the bottleneck.** Piper's `*-high` voices run at ~0.2×
   realtime (a 3 s sentence takes ~14 s). Switching to a `low` voice is ~2×
   realtime, and **espeak-ng is ~60× realtime** (instant, but robotic). Both are
   included here; pick one.
2. **A Home Assistant race dropped satellite audio**, leaving the satellite
   stuck "listening". `home-assistant/patch-ha-wyoming.sh` fixes it.

## Hardware used

The only hardware you need is a Raspberry Pi 4, a USB microphone and a speaker
connected to the headphone jack.

- Raspberry Pi 4 (4 GB or 8 GB), Raspberry Pi OS 64-bit
- A USB microphone/headset and a speaker or headphones
- Home Assistant running as a **Docker container** (`ghcr.io/home-assistant/home-assistant:stable`)

## Services (all in `docker-compose.yml`)

| service | image | port | role |
|---|---|---|---|
| `whisper` | `rhasspy/wyoming-whisper` | 10300 | STT — **sherpa-onnx streaming Zipformer** by default (fast); Whisper `tiny-int8` as an alternative |
| `piper` | `rhasspy/wyoming-piper` | 10200 | TTS — neural, good quality (~2× realtime) |
| `openwakeword` | derived | 10400 | wake word ("alexa") |
| `espeak` | `./espeak` (this repo) | 10500 | TTS — espeak-ng, robotic but ~60× realtime |
| `satellite` | `./satellite` (this repo) | 10700 | mic + speaker + on-device wake word |

All services bind to `127.0.0.1` and advertise over **zeroconf** so Home
Assistant auto-discovers them.

## Quick start

```bash
cp .env.example .env      # edit paths + audio devices
docker compose build      # builds the openwakeword shim, espeak server, satellite
docker compose up -d
```

Then in Home Assistant, the discovered Wyoming services appear under
**Settings → Devices & Services**; add each one (Whisper/sherpa, Piper, openWakeWord,
espeak-ng, PiSatellite). See `docs/setup.md` for the full walk-through.

## The Assist pipeline

Create/replace a pipeline with:

| stage | value |
|---|---|
| Conversation agent | your LLM agent (e.g. `conversation.deepseek_voice`) |
| Language | `en` |
| Speech-to-text | `stt.faster_whisper` (the sherpa model runs under this entity) |
| Text-to-speech | `tts.espeak_ng` (fast) or `tts.piper` (quality) |
| Wake word | `wake_word.openwakeword` / `alexa` |

`home-assistant/assist_pipeline.example.json` is a ready example.

## The LLM

This setup uses an OpenAI-compatible **Ollama** server. For a cloud model:

```bash
ollama pull deepseek-v4.1-flash:cloud
```

Then add the **Ollama** integration in Home Assistant (`http://127.0.0.1:11434`)
and create a conversation subentry (enable the **Assist** API so it can control
devices). Any HA conversation agent works — swap in `conversation.home_assistant`
for a fully offline assistant.

> Tip: use a prompt that keeps answers short and never asks clarifying questions,
> because this satellite re-arms the wake word after each turn (see Limitations).

## Measured speed (Raspberry Pi 4)

| stage | engine | result |
|---|---|---|
| Wake word | openWakeWord (on-device) | instant |
| STT | sherpa streaming Zipformer | **~1.4–1.6× realtime** (1.8 s speech → ~1.2 s) |
| STT | Whisper `tiny-int8` | ~0.3–0.6× realtime (slower: fixed 30 s encoder window) |
| LLM | cloud via Ollama | ~0.6–1.5 s (device commands ~0.05 s via local intents) |
| TTS | **espeak-ng** | **~60× realtime** (instant) |
| TTS | piper `*-low` | ~2× realtime |
| TTS | piper `*-high` | ~0.2× realtime (slow) |

End-to-end pipeline: **~1.1–1.8 s** per command. See `docs/speed.md`.

## Limitations

- **No continued conversation** on this satellite: answering a follow-up question
  requires saying the wake word again. (ESPHome satellites support this; the
  Wyoming satellite does not.)
- espeak-ng sounds robotic. piper sounds natural but is slower.
- Everything here is tuned for English; change the models/languages for others.

## Repository layout

```
docker-compose.yml            the whole stack
espeak/                       custom Wyoming espeak-ng TTS server
openwakeword/                 derived image (adds the zeroconf dependency)
satellite/                    derived image (upstream satellite + alsa-utils)
home-assistant/               example config, pipeline, and the HA race fix
docs/                         architecture, setup, speed, troubleshooting
```

## License and credits

This repository's own files are **MIT** licensed (see `LICENSE`).

It builds on and pulls in other projects, each under its own license:
- [`rhasspy/wyoming-*`](https://github.com/rhasspy) Docker images (Whisper, Piper, openWakeWord)
- [`rhasspy/wyoming-satellite`](https://github.com/rhasspy/wyoming-satellite) (cloned at build time)
- [espeak-ng](https://github.com/espeak-ng/espeak-ng)
- [Home Assistant](https://www.home-assistant.io/) and [openWakeWord](https://github.com/dscripka/openWakeWord)
