# Troubleshooting

## The satellite gets stuck in "listening" and never answers

**Symptom:** after a command the satellite's `assist_satellite` entity stays in
`listening`, and the next wake word does nothing. The satellite log shows
`Unexpected event from satellite: Event(type='audio-chunk', ...)`.

**Cause:** a race in Home Assistant's Wyoming satellite handler. When a new
pipeline starts while the previous one is still winding down, the old run's
`run-end` clears the "pipeline running" flag *after* the new run set it, so the
new run's microphone audio is discarded and it waits forever.

**Fix:** `home-assistant/patch-ha-wyoming.sh` (plus the systemd unit to re-apply
it after the HA container is rebuilt). It widens the audio-forwarding condition
so audio is kept whenever a pipeline task exists. See `docs/setup.md` step 5.

## Wake word works but there's no sound

- The satellite plays through its `--snd-command` (e.g. `aplay -D plughw:2,0`).
  Make sure that's your actual output device (`aplay -l`). On a Pi, card 2 is
  often the 3.5 mm jack, card 3 a USB headset.
- The mic is `--mic-command` (`arecord -l`). If the mic is muted or the wrong
  card, the wake word won't trigger.
- Confirm the service is healthy: `docker logs wyoming-satellite`.

## No TTS audio / distorted audio

The satellite resamples the TTS rate to its `--snd-command` rate, so a 16 kHz
voice (piper `*-low`) works with a 22050 Hz output. If in doubt, use a voice whose
sample rate matches your `--snd-command` (piper mediums are 22050 Hz).

## Home Assistant doesn't discover a service

- The service must advertise zeroconf **and** bind to an address HA can reach.
  The official images advertise their `0.0.0.0` bind address, which HA ignores;
  this repo binds services to `127.0.0.1`.
- If you previously added the service by hand (source `user`), HA will not
  re-discover it — remove the old entry first.
- Check `docker logs` for the service and whether it printed "Ready".

## The assistant asks a question back and then ignores my answer

This is expected. The Wyoming satellite **re-arms the wake word after every
turn**, so continued conversation (answering without saying "Alexa" again) does
not work here. Options:

- Tell the LLM (in its prompt) to never ask clarifying questions — pick the most
  likely target and act.
- Use the `assist_satellite.ask_question` service in a script/automation, which
  keeps the microphone open for one answer.
- Switch to an **ESPHome** voice satellite, which forwards `continue_conversation`.

## First response after a restart is slow

Model loading happens on first use. Give the stack a warm-up command after
`docker compose up`, or accept one slow first response.

## Rotating the model / voice / wake word

Everything is in `.env`:

- `--model`/`--stt-library` (STT), `PIPER_VOICE`/`ESPEAK_VOICE` (TTS),
  `WAKE_WORD` (wake word). Edit `.env` and `docker compose up -d`.
