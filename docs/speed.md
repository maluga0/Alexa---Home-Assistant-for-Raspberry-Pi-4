# Speed

All numbers measured on a Raspberry Pi 4 (4 cores @ 1.8 GHz). "× realtime" means
audio seconds produced per second of compute — higher is better; 1× or more means
faster than you can listen.

## Per stage

| stage | engine | throughput | a 2 s utterance costs |
|---|---|---|---|
| Wake word | openWakeWord (on-device) | — | ~0.15 s |
| **STT** | **sherpa streaming Zipformer** | **~1.4–1.6×** | **~1.2 s** |
| STT | Whisper `tiny-int8` | ~0.3–0.6× | ~3.5–4 s |
| LLM | cloud model via Ollama | — | 0.6–1.5 s (0.05 s for device commands) |
| **TTS** | **espeak-ng** | **~60×** | **~0.03 s** |
| TTS | piper `en_GB-alan-low` | ~2× | ~1 s |
| TTS | piper `en_GB-cori-high` | ~0.22× | ~9 s |

End-to-end pipeline (STT → LLM → TTS): **~1.1–1.8 s** per command.

## The two big wins

### 1. Speech-to-text: use the streaming model

Whisper's encoder processes a **fixed 30-second window**, so short commands pay a
constant floor no matter how little you said. The `rhasspy/wyoming-whisper` image
also ships **sherpa-onnx**, whose **streaming Zipformer** has no such floor and
transcribes incrementally:

```
--stt-library sherpa --sherpa-streaming \
--model sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06
```

This is ~3–4× faster than Whisper `tiny-int8` here, with equal or better accuracy.

### 2. Text-to-speech: pick the right voice / engine

Piper's quality tiers are not equal on ARM:

| voice | size | throughput |
|---|---|---|
| `en_GB-cori-high` | 114 MB | 0.22× |
| `en_GB-cori-medium` | 64 MB | ~1.4× |
| `en_GB-alan-low` | 63 MB | ~2× |

For maximum speed, use **espeak-ng** (~60×, robotic). For quality, use a piper
`*-low` or `*-medium` voice — **never `*-high` on a Pi 4**.

## Things that don't help (measured)

- More threads (`OMP_NUM_THREADS`) for piper/whisper.
- Pinning to a CPU core (`taskset`).
- int8-quantizing the piper model (VITS is conv-bound; dynamic int8 gave ~0%).
- A `--vad-filter` on Whisper (it was slower).

## Background load

`wyoming-openwakeword` runs continuously and uses ~25% of one core. Other
always-on services on the Pi add contention; piper is largely single-threaded, so
a quieter box helps TTS latency.
