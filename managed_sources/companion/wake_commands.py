"""Compose a detected command phrase and STT suffix; no detection or execution.

This module is not installed in the live pipeline. Its output carries no
identity or authorization: particularly, ``odemkni`` must never bypass the
door-lock authorization policy.
"""
import re
import unicodedata


def _normal(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(c)).strip(' .!?')


COMMANDS = {'rozsvit': 'rozsviť', 'zhasni': 'zhasni',
            'zamkni': 'zamkni', 'odemkni': 'odemkni'}


def compose(activation, suffix):
    """Return command text, None for ordinary wake words, or reject conflicts."""
    if not isinstance(activation, str) or _normal(activation) not in COMMANDS:
        return None
    if not isinstance(suffix, str):
        raise ValueError('invalid_transcript')
    phrase = _normal(activation)
    suffix = ' '.join(suffix.split())
    words = re.findall(r'\w+', _normal(suffix))
    verbs = [(i, word) for i, word in enumerate(words) if word in COMMANDS]
    if verbs:
        if len(verbs) != 1 or verbs[0] != (0, phrase):
            raise ValueError('conflicting_or_multiple_commands')
        return suffix
    return COMMANDS[phrase] + (' ' + suffix if suffix else '')
