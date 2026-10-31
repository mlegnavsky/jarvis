"""Local bounded metadata log; no tokens, request bodies or home snapshots."""
import json
import os
from pathlib import Path
from .ha import now


class Audit:
    def __init__(self, directory):
        self.path = Path(directory) / 'audit.jsonl'

    def write(self, operation, outcome):
        if self.path.exists() and self.path.stat().st_size >= 1024 * 1024:
            self.path.replace(self.path.with_suffix('.previous'))
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'a') as stream:
            stream.write(json.dumps({'at': now(), 'operation': operation, 'outcome': outcome}) + '\n')
