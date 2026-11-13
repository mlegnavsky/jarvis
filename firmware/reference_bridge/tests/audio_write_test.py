"""Compile the real on_audio_write method with host hardware substitutes.

Method text is extracted automatically, never copied into a parallel model.
The regression detects zero-progress spinning and delays inside the lease lock.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "components/jarvis_reference/jarvis_reference.cpp").read_text()
start = source.index("size_t ReferenceSpeaker::on_audio_write(")
brace = source.index("{", start)
depth = 1
end = brace + 1
while depth:
    depth += (source[end] == "{") - (source[end] == "}")
    end += 1
with tempfile.TemporaryDirectory(prefix="reference-audio-write-") as tmp:
    work = Path(tmp)
    impl = work / "audio_write_impl.inc"
    impl.write_text(source[start:end] + "\n")
    binary = work / "test"
    for tick_ms in (1, 10):
        subprocess.run(["g++", "-std=c++17", "-O1", "-g", "-Wall", "-Wextra", "-Werror", "-pthread",
                        "-fsanitize=undefined", "-fno-sanitize-recover=all",
                        "-I", str(ROOT / "components/jarvis_reference"),
                        f'-DADAPTER_WRITE_IMPL="{impl}"', f"-DTEST_TICK_MS={tick_ms}",
                        str(ROOT / "tests/audio_write_test.cpp"), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
