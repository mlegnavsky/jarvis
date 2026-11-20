"""Lossless compressed statistics archive. Recorder is opened read-only; no purge."""
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import sqlite3
import time

FIELDS = ('start_ts', 'mean', 'mean_weight', 'min', 'max', 'state', 'sum', 'last_reset_ts')
TABLES = (('5min', 'statistics_short_term'), ('hour', 'statistics'))


def decode(data, digest):
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Statistics archive checksum mismatch')
    try:
        rows = json.loads(gzip.decompress(data))
        if not isinstance(rows, list) or any(not isinstance(r, list) or len(r) != len(FIELDS) for r in rows):
            raise ValueError('Invalid statistics archive shape')
        return rows
    except (OSError, EOFError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid compressed statistics archive') from exc


def capture(source, target):
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve() or source.is_symlink() or target.is_symlink():
        raise ValueError('Unsafe statistics archive path')
    target.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True, timeout=15)
    dst = sqlite3.connect(target, timeout=15)
    os.chmod(target, 0o600)
    result = {'schema': 1, 'fields': FIELDS, 'source_rows': {}, 'archive_rows': {}, 'source_written': False}
    try:
        src.execute('PRAGMA query_only=ON')
        src.execute('BEGIN')  # One consistent WAL snapshot across both tables.
        dst.execute('''CREATE TABLE IF NOT EXISTS blocks(
            period TEXT NOT NULL, statistic_id TEXT NOT NULL, unit TEXT NOT NULL,
            day INTEGER NOT NULL, data BLOB NOT NULL, sha256 TEXT NOT NULL,
            nrows INTEGER NOT NULL, PRIMARY KEY(period,statistic_id,unit,day))''')
        dst.execute('CREATE TABLE IF NOT EXISTS receipts(captured_at REAL PRIMARY KEY, body TEXT NOT NULL)')
        with dst:
            for period, table in TABLES:
                columns = {r[1] for r in src.execute('PRAGMA table_info(' + table + ')')}
                if not {'metadata_id', 'start_ts'} <= columns:
                    raise sqlite3.OperationalError('Missing statistics table or timestamp')
                values = ','.join('s.' + f if f in columns else 'NULL' for f in FIELDS)
                cursor = src.execute('SELECT m.statistic_id,coalesce(m.unit_of_measurement,\'\'),'
                    'CAST(s.start_ts/86400 AS INTEGER),' + values + ' FROM ' + table + ' s '
                    'JOIN statistics_meta m ON m.id=s.metadata_id '
                    'WHERE s.start_ts IS NOT NULL ORDER BY 1,2,3,s.start_ts')
                count = 0
                for key, group in itertools.groupby(cursor, lambda row: row[:3]):
                    incoming = [list(row[3:]) for row in group]
                    count += len(incoming)
                    old = dst.execute('SELECT data,sha256 FROM blocks WHERE period=? AND statistic_id=? AND unit=? AND day=?', (period, *key)).fetchone()
                    merged = {row[0]: row for row in decode(*old)} if old else {}
                    merged.update((row[0], row) for row in incoming)
                    rows = [merged[t] for t in sorted(merged)]
                    data = gzip.compress(json.dumps(rows, separators=(',', ':'), allow_nan=False).encode(), mtime=0)
                    digest = hashlib.sha256(data).hexdigest()
                    dst.execute('INSERT OR REPLACE INTO blocks VALUES(?,?,?,?,?,?,?)', (period, *key, data, digest, len(rows)))
                    saved = dst.execute('SELECT data,sha256 FROM blocks WHERE period=? AND statistic_id=? AND unit=? AND day=?', (period, *key)).fetchone()
                    proof = {row[0]: row for row in decode(*saved)}
                    if any(proof.get(row[0]) != row for row in incoming):
                        raise ValueError('Statistics archive readback mismatch')
                result['source_rows'][period] = count
                result['archive_rows'][period] = dst.execute('SELECT coalesce(sum(nrows),0) FROM blocks WHERE period=?', (period,)).fetchone()[0]
                if result['archive_rows'][period] < count:
                    raise ValueError('Statistics archive coverage mismatch')
            if dst.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('Statistics archive integrity check failed')
            result['captured_at'] = time.time()
            dst.execute('INSERT INTO receipts VALUES(?,?)', (result['captured_at'], json.dumps(result)))
            # Keep bounded operational receipts; measurement blocks are never deleted.
            dst.execute('DELETE FROM receipts WHERE captured_at NOT IN (SELECT captured_at FROM receipts ORDER BY captured_at DESC LIMIT 100)')
        result['archive_bytes'] = target.stat().st_size
        result['source_bytes'] = source.stat().st_size
        return result
    finally:
        src.close()
        dst.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('target')
    args = parser.parse_args()
    print(json.dumps(capture(args.source, args.target), ensure_ascii=False))
