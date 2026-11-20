import gzip
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('summary_archive', Path('managed_sources/recorder_retention/archive.py'))
archive = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(archive)
except FileNotFoundError:
    archive = None


class SummaryArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / 'recorder.db'
        self.target = Path(self.tmp.name) / 'summaries.sqlite'
        with sqlite3.connect(self.source) as db:
            db.executescript('''
                CREATE TABLE statistics_meta(id INTEGER PRIMARY KEY, statistic_id TEXT, unit_of_measurement TEXT);
                INSERT INTO statistics_meta VALUES(1, 'sensor.power', 'W');
                CREATE TABLE statistics_short_term(id INTEGER PRIMARY KEY, metadata_id INTEGER, start_ts REAL, mean REAL, min REAL, max REAL, state REAL, sum REAL);
                CREATE TABLE statistics AS SELECT * FROM statistics_short_term;
                INSERT INTO statistics_short_term VALUES(1,1,300,12,5,20,NULL,NULL);
                INSERT INTO statistics_short_term VALUES(2,1,600,14,6,22,NULL,NULL);
                INSERT INTO statistics VALUES(1,1,0,10,3,25,100,80);
            ''')

    def test_preserves_all_available_statistics_and_never_modifies_source(self):
        self.assertIsNotNone(archive, 'summary archive is missing')
        before = self.source.read_bytes()
        result = archive.capture(self.source, self.target)
        self.assertEqual(result['source_rows'], {'5min': 2, 'hour': 1})
        self.assertEqual(result['archive_rows'], {'5min': 2, 'hour': 1})
        self.assertEqual(self.source.read_bytes(), before)
        with sqlite3.connect(self.target) as db:
            block = db.execute("SELECT data,sha256 FROM blocks WHERE period='5min'").fetchone()
        rows = archive.decode(*block)
        self.assertEqual(rows[0][1:], [12, None, 5, 20, None, None, None])

    def test_partial_day_replay_preserves_rows_already_removed_from_source(self):
        self.assertIsNotNone(archive)
        archive.capture(self.source, self.target)
        with sqlite3.connect(self.source) as db:
            db.execute('DELETE FROM statistics_short_term WHERE start_ts=300')
            db.execute('INSERT INTO statistics_short_term VALUES(3,1,900,16,7,23,NULL,NULL)')
        result = archive.capture(self.source, self.target)
        self.assertEqual(result['archive_rows']['5min'], 3)
        again = archive.capture(self.source, self.target)
        self.assertEqual(again['archive_rows']['5min'], 3)

    def test_rebound_metadata_ids_do_not_overwrite_another_sensor(self):
        self.assertIsNotNone(archive)
        archive.capture(self.source, self.target)
        with sqlite3.connect(self.source) as db:
            db.execute("UPDATE statistics_meta SET statistic_id='sensor.other',unit_of_measurement='C' WHERE id=1")
        archive.capture(self.source, self.target)
        with sqlite3.connect(self.target) as db:
            self.assertEqual(db.execute('SELECT count(DISTINCT statistic_id) FROM blocks').fetchone()[0], 2)

    def test_corruption_is_not_silently_replaced(self):
        self.assertIsNotNone(archive)
        archive.capture(self.source, self.target)
        with sqlite3.connect(self.target) as db:
            db.execute("UPDATE blocks SET data=x'0001' WHERE period='5min'")
        with self.assertRaises(ValueError):
            archive.capture(self.source, self.target)

    def test_incomplete_source_cannot_claim_success(self):
        self.assertIsNotNone(archive)
        with sqlite3.connect(self.source) as db:
            db.execute('DROP TABLE statistics')
        with self.assertRaises(sqlite3.OperationalError):
            archive.capture(self.source, self.target)
