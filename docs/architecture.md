# Architecture

## Components

All speech components are separate processes/containers that Home Assistant
talks to over the **Wyoming** protocol (plain TCP + JSON events). Home Assistant
itself runs as a **Docker container** (a "Container install" — no Supervisor, so
there are no add-ons; the services below replace them).

| component | container | default port |
|---|---|---|
| Speech-to-text | `wyoming-whisper` (runs sherpa-onnx or Whisper) | 10300 |
| Text-to-speech (neural) | `wyoming-piper` | 10200 |
| Wake word | `wyoming-openwakeword` | 10400 |
| Text-to-speech (fast) | `wyoming-espeak` (this repo) | 10500 |
| Satellite (mic + speaker) | `wyoming-satellite` | 10700 |

Home Assistant (host network) reaches them on `127.0.0.1`.

## Data flow for one command

```
"You say: Alexa, turn on the kitchen light"
        │
        ▼
[satellite]  streams microphone audio to [openwakeword] (always on)
        │        openWakeWord matches "alexa"
        │  satellite tells HA "wake detected" and streams mic audio to HA
        ▼
[HA Assist pipeline]
        1. STT   : streams audio to [whisper]; transcript "turn on the kitchen light"
        2. Intent: conversation agent (LLM) -> "Turned on the living room light."
        3. TTS   : sends text to [espeak] -> PCM audio
        4. play  : streams PCM back to the satellite -> aplay out the speaker
```

## Discovery

Every service runs with `--zeroconf` and advertises `_wyoming._tcp.local.`.
Home Assistant's Wyoming integration discovers them automatically. On a
**Container** install the services must bind to an address Home Assistant can
reach — this repo binds them to `127.0.0.1`, which is what the discovered entry
uses.

> Note: the official containers pass their `0.0.0.0` bind address to zeroconf,
> which Home Assistant rejects. Binding to `127.0.0.1` avoids that.

## Why espeak-ng

Piper is neural and, on a Pi 4, its `high` voices are ~0.2× realtime (too slow for
conversation). espeak-ng is a formant synthesizer: robotic, but ~60× realtime, so
TTS stops being a bottleneck. Both are included so you can choose.

## Why sherpa-onnx for STT

Whisper reserves a fixed **30-second encoder window**, so even a 2-second command
costs a few seconds. The sherpa-onnx **streaming Zipformer** has no such floor and
transcribes as you speak, making it several times faster with comparable accuracy.
