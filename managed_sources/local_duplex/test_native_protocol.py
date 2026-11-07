"""Characterize pinned device microphone lifecycle, independent of HA doubles."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NativeMicrophoneTests(unittest.TestCase):
    def test_no_vad_end_retains_stream_and_run_end_releases_it(self):
        compiler=shutil.which('g++')
        if compiler is None:self.skipTest('g++ needed for pinned native protocol characterization')
        fixture=Path(__file__).parents[1]/'voice_diagnostics/test_data/esphome_terminal_2026_10_1.cpp'
        with tempfile.TemporaryDirectory() as directory:
            binary=Path(directory)/'native'
            subprocess.run([compiler,'-std=c++17',str(fixture),'-o',str(binary)],check=True,capture_output=True)
            for events,expected in (('', 'STREAMING_MICROPHONE 1'),
                                    ('stt-vad-end\n','AWAITING_RESPONSE 0'),
                                    ('run-end\n','IDLE 0')):
                with self.subTest(events=events):
                    result=subprocess.run([str(binary),'STREAMING_MICROPHONE','microphone'],
                        input=events,text=True,capture_output=True,check=True)
                    self.assertEqual(result.stdout.strip(),expected)
