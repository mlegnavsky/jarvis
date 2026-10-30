"""Jarvis Speaker Lab: event-driven conversation controller.

No microphone capture or biometric enrollment is performed here. Adapters supply
wake word, VAD, speaker verification and TTS events. No production HA actions.
"""
from dataclasses import dataclass
from enum import Enum
from time import monotonic
from typing import Optional


class Mode(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    SPEAKING = "speaking"


@dataclass
class SpeakerConfig:
    wake_phrases: tuple[str, ...] = ("jarvisi",)
    followup_seconds: float = 3.0
    min_speaker_confidence: float = 0.80
    require_wake_for_each_turn: bool = False


class SpeakerController:
    def __init__(self, config: Optional[SpeakerConfig] = None, clock=monotonic):
        self.config = config or SpeakerConfig()
        self.clock = clock
        self.mode = Mode.IDLE
        self.followup_deadline = 0.0
        self.speaker_id: Optional[str] = None
        self.interrupt_tts = False

    def wake(self, phrase: str) -> bool:
        if phrase.strip().casefold() not in self.config.wake_phrases:
            return False
        self.mode = Mode.LISTENING
        self.followup_deadline = self.clock() + self.config.followup_seconds
        return True

    def voice_identity(self, identity: Optional[str], confidence: float) -> None:
        # A voice match is a conversational hint, NOT authentication.
        self.speaker_id = identity if identity and confidence >= self.config.min_speaker_confidence else None

    def speech_started(self) -> bool:
        """Call immediately on VAD speech onset, even during TTS playback."""
        if self.mode == Mode.SPEAKING:
            self.interrupt_tts = True
            self.mode = Mode.LISTENING
            self.followup_deadline = self.clock() + self.config.followup_seconds
            return True
        return False

    def response_started(self) -> None:
        self.interrupt_tts = False
        self.mode = Mode.SPEAKING

    def response_finished(self) -> None:
        self.mode = Mode.LISTENING
        self.followup_deadline = self.clock() + self.config.followup_seconds

    def tick(self) -> None:
        if self.mode == Mode.LISTENING and (
            self.config.require_wake_for_each_turn or self.clock() >= self.followup_deadline
        ):
            self.mode = Mode.IDLE
            self.speaker_id = None
