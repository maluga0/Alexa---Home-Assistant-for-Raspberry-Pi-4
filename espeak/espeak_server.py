#!/usr/bin/env python3
"""Minimal Wyoming text-to-speech server backed by espeak-ng.

Speaks the subset of the Wyoming protocol Home Assistant needs (Describe +
Synthesize / streaming synthesize) so HA auto-discovers it as a normal TTS
engine. espeak-ng is a formant synthesizer, so synthesis is far faster than
realtime on any CPU.
"""

import argparse
import asyncio
import logging
import signal
import subprocess
import wave
from functools import partial
from io import BytesIO

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.error import Error
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer, AsyncTcpServer
from wyoming.tts import (
    Synthesize,
    SynthesizeChunk,
    SynthesizeStart,
    SynthesizeStop,
    SynthesizeStopped,
)

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = Attribution(name="espeak-ng", url="https://github.com/espeak-ng/espeak-ng")
PROGRAM_NAME = "espeak-ng"


def _espeak_version() -> str:
    try:
        out = subprocess.run(
            ["espeak-ng", "--version"], capture_output=True, text=True, check=False
        ).stdout
        for line in out.splitlines():
            if line.startswith("eSpeak NG"):
                # e.g. "eSpeak NG text-to-speech: 1.51  Data at: /usr/lib/..."
                return line.split(":", 1)[1].split()[0]
    except OSError:
        pass
    return ""


def _list_voices() -> list[TtsVoice]:
    """Enumerate espeak-ng voices; each advertised voice's language is its
    primary subtag so Home Assistant can match pipeline languages."""
    voices: list[TtsVoice] = []
    try:
        out = subprocess.run(
            ["espeak-ng", "--voices"], capture_output=True, text=True, check=False
        ).stdout
    except OSError:
        return voices

    seen: set[str] = set()
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        lang = parts[1]  # e.g. "en-gb"
        if lang in seen:
            continue
        seen.add(lang)
        voices.append(
            TtsVoice(
                name=lang,
                languages=[lang.split("-")[0]],
                attribution=ATTRIBUTION,
                installed=True,
                description=lang,
                version=None,
            )
        )

    # Stable, case-correct language tags
    for v in voices:
        v.languages = [l.lower() for l in v.languages]
    return voices


def _run_espeak(text: str, voice: str, rate: int, pitch: int, amplitude: int) -> bytes:
    proc = subprocess.run(
        [
            "espeak-ng",
            "--stdout",
            "-v",
            voice,
            "-s",
            str(rate),
            "-p",
            str(pitch),
            "-a",
            str(amplitude),
            text,
        ],
        capture_output=True,
        check=True,
    )
    return proc.stdout


class EspeakHandler(AsyncEventHandler):
    def __init__(self, info_factory, args: argparse.Namespace, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self.info_factory = info_factory
        self.args = args
        self._stream_voice: str | None = None
        self._stream_text: list[str] = []

    async def _synthesize(self, text: str, voice: str | None) -> None:
        text = " ".join(text.splitlines()).strip()
        voice = voice or self.args.voice
        if not text:
            await self.write_event(AudioStop().event())
            return

        wav_bytes = await asyncio.to_thread(
            _run_espeak, text, voice, self.args.rate, self.args.pitch, self.args.amplitude
        )

        with wave.open(BytesIO(wav_bytes), "rb") as wav:
            rate = wav.getframerate()
            width = wav.getsampwidth()
            channels = wav.getnchannels()
            frames = wav.readframes(wav.getnframes())

        await self.write_event(
            AudioStart(rate=rate, width=width, channels=channels).event()
        )

        bytes_per_chunk = width * channels * self.args.samples_per_chunk
        for i in range(0, len(frames), bytes_per_chunk):
            chunk = frames[i : i + bytes_per_chunk]
            if not chunk:
                continue
            await self.write_event(
                AudioChunk(
                    rate=rate, width=width, channels=channels, audio=chunk
                ).event()
            )

        await self.write_event(AudioStop().event())

    async def handle_event(self, event: Event) -> bool:
        try:
            if Describe.is_type(event.type):
                await self.write_event(self.info_factory().event())
                return True

            if Synthesize.is_type(event.type):
                synthesize = Synthesize.from_event(event)
                voice = synthesize.voice.name if synthesize.voice else None
                await self._synthesize(synthesize.text, voice)
                return True

            if SynthesizeStart.is_type(event.type):
                start = SynthesizeStart.from_event(event)
                self._stream_voice = start.voice.name if start.voice else None
                self._stream_text = []
                return True

            if SynthesizeChunk.is_type(event.type):
                self._stream_text.append(SynthesizeChunk.from_event(event).text)
                return True

            if SynthesizeStop.is_type(event.type):
                await self._synthesize(" ".join(self._stream_text), self._stream_voice)
                await self.write_event(SynthesizeStopped().event())
                self._stream_text = []
                return True
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Synthesis error")
            await self.write_event(
                Error(text=str(err), code=err.__class__.__name__).event()
            )
            return True

        return True


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", required=True, help="tcp://host:port")
    parser.add_argument("--voice", default="en", help="Default espeak-ng voice")
    parser.add_argument("--rate", type=int, default=175, help="Words per minute")
    parser.add_argument("--pitch", type=int, default=50, help="Pitch (0-99)")
    parser.add_argument("--amplitude", type=int, default=100, help="Amplitude (0-200)")
    parser.add_argument("--samples-per-chunk", type=int, default=1024)
    parser.add_argument(
        "--zeroconf",
        nargs="?",
        const=PROGRAM_NAME,
        default=None,
        help="Enable discovery over zeroconf with optional name",
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    voices = _list_voices()
    if not voices:
        voices = [
            TtsVoice(
                name=args.voice,
                languages=["en"],
                attribution=ATTRIBUTION,
                installed=True,
                description=args.voice,
                version=None,
            )
        ]

    def info_factory() -> Info:
        return Info(
            tts=[
                TtsProgram(
                    name=PROGRAM_NAME,
                    attribution=ATTRIBUTION,
                    installed=True,
                    description="eSpeak NG text-to-speech",
                    version=_espeak_version(),
                    voices=voices,
                )
            ]
        )

    server = AsyncServer.from_uri(args.uri)

    if args.zeroconf:
        if not isinstance(server, AsyncTcpServer):
            raise ValueError("Zeroconf requires tcp:// uri")
        from wyoming.zeroconf import HomeAssistantZeroconf

        await HomeAssistantZeroconf(
            name=args.zeroconf, port=server.port, host=server.host
        ).register_server()
        _LOGGER.debug("Zeroconf discovery enabled")

    _LOGGER.info("Ready")
    server_task = asyncio.create_task(
        server.run(partial(EspeakHandler, info_factory, args))
    )
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, server_task.cancel)
    loop.add_signal_handler(signal.SIGTERM, server_task.cancel)
    try:
        await server_task
    except asyncio.CancelledError:
        _LOGGER.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
