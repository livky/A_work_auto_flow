"""Bounded retry for Windows reader sharing conflicts; preserve failed payloads."""
import json
import os
from pathlib import Path
import time


def replace_with_retry(source, destination, attempts=6):
    """Retry only explicit Windows access/sharing/lock errors, not arbitrary IO.

    Readers without FILE_SHARE_DELETE can momentarily prevent atomic replace.
    Every conflict is appended to a sidecar even if a later attempt succeeds;
    exhausted retries leave the pending payload available for diagnosis.
    """
    destination = Path(destination)
    for attempt in range(attempts):
        try:
            os.replace(source, destination)
            return
        except OSError as exc:
            if getattr(exc, 'winerror', None) not in {5, 32, 33}:
                raise
            event = {'time': time.time(), 'attempt': attempt + 1,
                     'winerror': exc.winerror, 'error': str(exc),
                     'pending': str(source), 'destination': str(destination)}
            with destination.with_name(destination.name + '.write-events.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + '\n')
            if attempt + 1 == attempts:
                raise
            time.sleep(min(0.02 * (2 ** attempt), 0.32))
