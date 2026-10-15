# Setup

## 0. Prerequisites

- Raspberry Pi 4 running 64-bit Raspberry Pi OS, Docker + Docker Compose installed.
- A Home Assistant **Container** install with its config directory bind-mounted
  (e.g. `/home/pi/homeassistant-config:/config`).
- A microphone and speaker (a USB headset works well). Note the ALSA devices
  with `arecord -l` and `aplay -l`.

## 1. Configure and start the voice stack

```bash
git clone https://github.com/<your-user>/Alexa---Home-Assistant-for-Raspberry-Pi-4.git alexa
cd alexa
cp .env.example .env
nano .env            # set PI_CACHE_DIR and your MIC_COMMAND / SND_COMMAND
docker compose build
docker compose up -d
```

First start downloads models (Whisper/sherpa + Piper voice) — give it a minute.

## 2. Add the discovered services in Home Assistant

**Settings → Devices & Services → Discovered**. You should see:

- `faster-whisper` (the STT service)
- `piper`
- `openWakeWord`
- `espeak-ng`
- `PiSatellite`

Add each one (confirm the dialog). They will show up as entities:
`stt.faster_whisper`, `tts.piper`, `tts.espeak_ng`, `wake_word.openwakeword`,
`assist_satellite.pisatellite`.

> If a service was added before (e.g. a `127.0.0.1:port` entry you created by
> hand), Home Assistant will not re-discover it — remove the old entry first.

## 3. Set up the conversation agent (LLM)

Pick any Home Assistant conversation agent. This repo was built with a local
[Ollama](https://ollama.com) server using a cloud model:

```bash
ollama pull deepseek-v4.1-flash:cloud
```

In Home Assistant: **Settings → Devices & Services → Add Integration → Ollama**,
URL `http://127.0.0.1:11434`. Then add a **conversation** subentry for the model
and enable the **Assist** API (so it can control devices).

Give it a prompt like:

> You are the Home Assistant voice assistant. Be very brief: reply with at most
> one short sentence (about 10 words) in plain spoken text. Never use lists,
> markdown, or emojis. For device actions, confirm in a few words. Never ask the
> user a clarifying question: if a request is ambiguous, choose the most likely
> target yourself and carry it out.

(The "never ask a clarifying question" part matters — see Limitations in the
README.)

## 4. Create the Assist pipeline

**Settings → Voice assistants → Add assistant** (or edit the default one):

- Conversation agent: your LLM agent (e.g. *DeepSeek Voice*)
- Language: `English`
- Speech-to-text: `faster-whisper`
- Text-to-speech: `espeak-ng` (fast) or `piper` (quality)
- Wake word: `openwakeword` → `alexa`

Mark it as preferred. `home-assistant/assist_pipeline.example.json` is a ready
example of the stored pipeline.

## 5. (Recommended) Apply the Wyoming audio-race fix

See `docs/troubleshooting.md`. Copy the two files and enable the service:

```bash
sudo install -m0755 home-assistant/patch-ha-wyoming.sh /usr/local/sbin/
sudo install -m0644 home-assistant/patch-ha-wyoming.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now patch-ha-wyoming.service
```

## 6. Test

Say **"Alexa, what time is it?"**. The satellite should answer within a couple of
seconds. If not, see `docs/troubleshooting.md`.
