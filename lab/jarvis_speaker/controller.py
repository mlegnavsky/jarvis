"""Lab conversation policy. Trusted acoustic adapters supply verified events.

This is not a biometric verifier. Never feed identity from an LLM, transcript or
untrusted client here. Approved IDs refer to locally enrolled voice profiles.
Adapters must tag playback/echo and correlate callbacks with session_id.
"""
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from time import monotonic
from typing import Optional


class Mode(str, Enum):
    IDLE = 'idle'
    LISTENING = 'listening'
    CAPTURING = 'capturing'
    PROCESSING = 'processing'
    SPEAKING = 'speaking'


@dataclass(frozen=True)
class SpeakerConfig:
    wake_phrases: tuple[str, ...] = ('jarvisi',)
    followup_seconds: float = 3.0
    max_utterance_seconds: float = 30.0
    min_speaker_confidence: float = 0.80
    require_wake_for_each_turn: bool = False
    approved_speakers: frozenset[str] = frozenset()

    def __post_init__(self):
        if not isfinite(self.max_utterance_seconds) or self.max_utterance_seconds <= 0:
            raise ValueError('max_utterance_seconds must be positive and finite')
        if not isfinite(self.followup_seconds) or self.followup_seconds <= 0:
            raise ValueError('followup_seconds must be positive and finite')
        if not isfinite(self.min_speaker_confidence) or not 0 < self.min_speaker_confidence <= 1:
            raise ValueError('invalid speaker confidence threshold')


class SpeakerController:
    unknown_speaker_prompt = 'Neznám váš hlas, jak se jmenujete?'
    spoken_name = 'Jarvis'  # Czech J is an acoustic acceptance requirement.

    def __init__(self, config: Optional[SpeakerConfig] = None, clock=monotonic):
        self.config = config or SpeakerConfig()
        self.clock = clock
        self.mode = Mode.IDLE
        self.followup_deadline = 0.0
        self.speaker_id: Optional[str] = None
        self.interrupt_tts = False
        self.session_id = 0
        self.utterance_id = 0
        self.playback_id = 0
        self._proof_deadline = 0.0

    def _clear_identity(self):
        self.speaker_id = None
        self._proof_deadline = 0.0

    def wake(self, phrase: str, *, source: str = 'human') -> bool:
        self.tick()
        if source != 'human' or self.mode != Mode.IDLE:
            return False
        if phrase.strip().casefold() not in self.config.wake_phrases:
            return False
        self.session_id += 1
        self.utterance_id += 1
        self._clear_identity()
        self.interrupt_tts = False
        self.mode = Mode.LISTENING
        self.followup_deadline = self.clock() + self.config.followup_seconds
        return True

    def voice_identity(self, identity: Optional[str], confidence: float, *, utterance_id: int) -> None:
        if utterance_id != self.utterance_id:
            return
        self._clear_identity()
        self.tick()
        if self.mode not in (Mode.LISTENING, Mode.CAPTURING):
            return
        if identity and isfinite(confidence) and self.config.min_speaker_confidence <= confidence <= 1:
            self.speaker_id = identity
            self._proof_deadline = self.clock() + self.config.followup_seconds

    def authorize_command(self, *, utterance_id: int) -> bool:
        """Consume one current utterance's proof; caller dispatches only on True.

        Voice matches are probabilistic; do not use for locks, payments or other
        sensitive actions. No queued command is retained for a later introduction.
        """
        self.tick()
        allowed = (utterance_id == self.utterance_id
                   and self.mode in (Mode.LISTENING, Mode.CAPTURING)
                   and self.speaker_id in self.config.approved_speakers
                   and self.clock() < self._proof_deadline)
        self._clear_identity()
        if allowed:
            self.mode = Mode.PROCESSING
        return allowed

    def speech_started(self, *, source: str = 'human') -> bool:
        if source != 'human' or self.mode == Mode.IDLE:
            return False
        self._clear_identity()
        interrupted = self.mode == Mode.SPEAKING
        if interrupted:
            self.interrupt_tts = True
        self.utterance_id += 1
        self.mode = Mode.CAPTURING
        self.followup_deadline = self.clock() + self.config.max_utterance_seconds
        return interrupted

    def response_started(self, *, session_id: Optional[int] = None) -> None:
        if self.mode == Mode.IDLE or (session_id is not None and session_id != self.session_id):
            return
        self._clear_identity()
        self.interrupt_tts = False
        self.playback_id += 1
        self.mode = Mode.SPEAKING

    def response_finished(self, *, playback_id: int, session_id: Optional[int] = None) -> None:
        if playback_id != self.playback_id or self.mode != Mode.SPEAKING or (session_id is not None and session_id != self.session_id):
            return
        self._clear_identity()
        if self.config.require_wake_for_each_turn:
            self.end_session()
        else:
            self.mode = Mode.LISTENING
            self.followup_deadline = self.clock() + self.config.followup_seconds

    def end_session(self) -> None:
        self.mode = Mode.IDLE
        self.utterance_id += 1
        self._clear_identity()
        self.followup_deadline = 0.0
        self.interrupt_tts = False

    def tick(self) -> None:
        if self.mode in (Mode.LISTENING, Mode.CAPTURING) and self.clock() >= self.followup_deadline:
            self.end_session()
