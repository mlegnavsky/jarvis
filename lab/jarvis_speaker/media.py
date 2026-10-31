"""Conversation-wide ducking. Use the actual audio sink, not the video source.

Transport must implement get_volume(entity) and set_volume(entity, float) with
bounded timeouts. This module never pauses/stops media. Call end() in finally,
on timeout, cancellation and errors; retry while pending is nonempty. Crash
recovery requires a durable transport/session supervisor before deployment.
"""
from math import isfinite
from typing import Protocol


class VolumeTransport(Protocol):
    def get_volume(self, entity: str) -> float: ...
    def set_volume(self, entity: str, level: float) -> None: ...


class VolumeGuard:
    def __init__(self, transport: VolumeTransport, entities: tuple[str, ...],
                 *, duck_level: float = .15):
        if not isfinite(duck_level) or not 0 <= duck_level <= 1:
            raise ValueError('duck_level must be within [0, 1]')
        self.transport = transport
        self.entities = tuple(dict.fromkeys(entities))
        self.duck_level = duck_level
        self.active = False
        self._original: dict[str, float] = {}

    @property
    def pending(self) -> dict[str, float]:
        return dict(self._original)

    def begin(self) -> dict[str, str]:
        if self.active:
            return {}
        if self._original:
            raise RuntimeError('restore previous volume before starting another session')
        self.active = True
        errors = {}
        for entity in self.entities:
            try:
                volume = self.transport.get_volume(entity)
                if isinstance(volume, bool) or not isinstance(volume, (float, int)) or not isfinite(volume) or not 0 <= volume <= 1:
                    raise ValueError('unknown or invalid volume')
                # Snapshot before write: a timeout may mean a write succeeded.
                self._original[entity] = volume
                self.transport.set_volume(entity, min(volume, self.duck_level))
            except (OSError, ValueError, TimeoutError) as exc:
                errors[entity] = type(exc).__name__
        return errors

    def end(self) -> dict[str, str]:
        self.active = False
        errors = {}
        for entity, volume in tuple(self._original.items()):
            try:
                self.transport.set_volume(entity, volume)
            except (OSError, ValueError, TimeoutError) as exc:
                errors[entity] = type(exc).__name__
            else:
                del self._original[entity]
        return errors

