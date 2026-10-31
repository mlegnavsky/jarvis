"""Offline Anička lab simulator. No microphones, network, biometric or HA calls.

Run: python lab/jarvis_speaker/simulation.py --demo
Events are deliberately synthetic. Source tags are NOT acoustic detection.
All methods must be called serially, just like the policy controller.
"""
import argparse
import json
from math import isfinite

from controller import Mode, SpeakerConfig, SpeakerController
from media import VolumeGuard
from persona import VOICE_REQUIREMENTS, system_prompt


class Simulation:
    """Manually clocked fixtures that exercise actual policy and volume guard.

    Failure switches are part of the lab simulator, not hardware capabilities.
    Token = (session ID, utterance ID); output token = (session ID, playback ID).
    """
    microphones = {'living-room': 'obývák', 'child-room': 'dětský pokoj'}

    def __init__(self):
        self.now = 0.0
        self.ctrl = SpeakerController(SpeakerConfig(
            approved_speakers=frozenset({'fixture-owner'})), clock=lambda: self.now)
        self.volumes = {'tv': .7}
        self.lights = {'obývák': False, 'dětský pokoj': False}
        self.guard = VolumeGuard(self, ('tv',))
        self.output_available = True
        self.stop_available = True
        self.volume_available = True
        self.playback = None
        self.reply = ''
        self.actions = []
        self.trace = []
        self._capture = None
        self._room = None
        self._output_deadline = 0.0
        self._session_deadline = 0.0

    def get_volume(self, entity):
        if not self.volume_available:
            raise OSError('simulated volume transport unavailable')
        return self.volumes[entity]

    def set_volume(self, entity, level):
        if not self.volume_available:
            raise OSError('simulated volume transport unavailable')
        self.volumes[entity] = level

    def _record(self, event):
        self.trace.append({'event': event, 'at': self.now,
                           'session': self.ctrl.session_id,
                           'utterance': self.ctrl.utterance_id})

    def _stop(self):
        if self.playback is not None:
            if not self.stop_available:
                self._record('stop_failed')
                return False
            self.playback = None
            self._record('output_stopped')
        return True

    def close(self):
        self.ctrl.end_session()
        self._capture = None
        self._room = None
        self._stop()
        self.guard.end()
        self._record('session_closed')

    def advance(self, seconds):
        if isinstance(seconds, bool) or not isfinite(seconds) or seconds < 0:
            raise ValueError('time must advance by a finite nonnegative number')
        self.now += seconds
        self.ctrl.tick()
        if self.ctrl.mode != Mode.IDLE and (
            self.now >= self._session_deadline or
            (self.playback is not None and self.now >= self._output_deadline)
        ):
            self.close()
        elif self.ctrl.mode == Mode.IDLE:
            self._capture = None
            self._stop()
            self.guard.end()  # Also retries pending restoration after failures.

    def wake(self, phrase, *, source='human'):
        self.advance(0)
        if self.playback is not None or self.guard.pending:
            return False
        if not self.ctrl.wake(phrase, source=source):
            return False
        self._session_deadline = self.now + 120.0
        self.guard.begin()
        self._record('wake')
        return True

    def speech(self, *, mic='living-room', source='human'):
        self.advance(0)
        if source != 'human' or mic not in self.microphones or self.ctrl.mode == Mode.IDLE:
            return None
        # Stop the output before accepting the next command, even if identity
        # verification has not finished. On stop failure, fail closed.
        if not self._stop():
            self.close()
            return None
        self.ctrl.speech_started(source=source)
        self._room = self.microphones[mic]
        self._capture = (self.ctrl.session_id, self.ctrl.utterance_id)
        self._record('speech')
        return self._capture

    def submit(self, token, text, *, speaker=None, confidence=0.0):
        self.advance(0)
        if (token is None or token != self._capture or
                token != (self.ctrl.session_id, self.ctrl.utterance_id) or
                self.ctrl.mode != Mode.CAPTURING):
            self._record('stale_or_inactive_input')
            return
        self._capture = None
        self.ctrl.voice_identity(speaker, confidence, utterance_id=token[1])
        if not self.ctrl.authorize_command(utterance_id=token[1]):
            self._record('denied')
            self._respond(self.ctrl.unknown_speaker_prompt)
            return
        command = text.strip().casefold()
        if command in ('rozsviť', 'zhasni'):
            enabled = command == 'rozsviť'
            self.lights[self._room] = enabled
            self.actions.append({'room': self._room, 'on': enabled,
                                 'profile': speaker, 'session': token[0],
                                 'utterance': token[1]})
            self._record('simulated_light_changed')
            reply = 'Rozsvítila jsem.' if enabled else 'Zhasla jsem.'
        elif command == 'jak se jmenuješ':
            reply = 'Jsem Anička. S čím ti pomůžu?'
        else:
            reply = 'Tohle je zatím simulace. Zkus „rozsviť“, „zhasni“ nebo „jak se jmenuješ“.'
        self._respond(reply)

    def _respond(self, text):
        if not self.output_available:
            self.close()
            raise OSError('simulated output unavailable')
        self.ctrl.response_started(session_id=self.ctrl.session_id)
        self.reply = text
        self.playback = (self.ctrl.session_id, self.ctrl.playback_id)
        self._output_deadline = self.now + 30.0
        self._record('simulated_output_started')

    def complete(self, token):
        self.advance(0)
        if token is None or token != self.playback or self.ctrl.mode != Mode.SPEAKING:
            return
        self.playback = None
        self.ctrl.response_finished(session_id=token[0], playback_id=token[1])
        self._record('output_finished')
        self.advance(0)


def demo():
    """Six independently checked complete simulated conversations."""
    report = []

    def row(name, passed):
        report.append({'scenario': name, 'passed': bool(passed), 'simulation': True})

    def turn(sim, text, speaker='fixture-owner'):
        sim.submit(sim.speech(), text, speaker=speaker, confidence=.99)
        return sim.playback

    sim = Simulation()
    woke = sim.wake('Aničko')
    out = turn(sim, 'rozsviť')
    sim.complete(out)
    sim.advance(3)
    row('Probuzení Aničko, světlo a obnovení TV', woke and sim.lights['obývák']
        and sim.volumes['tv'] == .7 and sim.ctrl.mode == Mode.IDLE)

    sim = Simulation()
    sim.wake('Aničko')
    sim.complete(turn(sim, 'jak se jmenuješ'))
    sim.advance(2)
    sim.complete(turn(sim, 'rozsviť'))
    sim.advance(3)
    row('Navazující rozhovor do tří sekund', sim.lights['obývák'] and sim.volumes['tv'] == .7)

    sim = Simulation()
    sim.wake('Aničko')
    for text in ('rozsviť', 'Jmenuji se Martin', 'rozsviť'):
        sim.complete(turn(sim, text, speaker='unknown'))
    sim.advance(3)
    row('Neznámý hlas a představení bez oprávnění', not sim.actions and sim.volumes['tv'] == .7)

    sim = Simulation()
    sim.wake('Aničko')
    old = turn(sim, 'rozsviť')
    new = turn(sim, 'zhasni')
    sim.complete(old)
    ignored = sim.playback == new
    sim.complete(new)
    sim.advance(3)
    row('Přerušení odpovědi a opožděný callback', ignored and not sim.lights['obývák']
        and any(e['event'] == 'output_stopped' for e in sim.trace))

    sim = Simulation()
    rejected = not sim.wake('Aničko', source='playback')
    sim.wake('Aničko')
    out = turn(sim, 'jak se jmenuješ')
    ignored = sim.speech(source='echo') is None and sim.playback == out
    sim.complete(out)
    sim.advance(3)
    row('Syntetický TV/HomePod zdroj odmítnut', rejected and ignored)

    sim = Simulation()
    sim.wake('Aničko')
    sim.output_available = False
    try:
        turn(sim, 'jak se jmenuješ')
    except OSError:
        pass
    row('Chyba výstupu obnoví TV', sim.ctrl.mode == Mode.IDLE and sim.volumes['tv'] == .7)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', help='run six offline scenarios')
    parser.add_argument('--persona', action='store_true', help='export persona/voice requirements')
    args = parser.parse_args()
    if args.persona:
        print(json.dumps({'system_prompt': system_prompt(), 'voice': VOICE_REQUIREMENTS}, ensure_ascii=False, indent=2))
    if args.demo:
        results = demo()
        print(json.dumps({'mode': 'offline simulation', 'results': results}, ensure_ascii=False, indent=2))
        raise SystemExit(0 if all(row['passed'] for row in results) else 1)
    if not args.persona:
        parser.print_help()
