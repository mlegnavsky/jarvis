"""Compile the real adapter header/methods with host-only hardware substitutes.

The stock callback substitute re-enters the actual gate. This catches missing
delegation, reference identity leaks, callback lock inversion and rearm races.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="reference-stock-adapter-") as tmp:
    work = Path(tmp)
    header = (ROOT / "components/jarvis_reference/jarvis_reference.h").read_text()
    header = re.sub(r'^#include "esphome/[^\n]+\n', '', header, flags=re.M)
    header = header.replace(" private:", " public:")  # expose state to the host harness only
    (work / "adapter_header.inc").write_text(header)
    source = (ROOT / "components/jarvis_reference/jarvis_reference.cpp").read_text()
    source = re.sub(r'^#include [^\n]+\n', '', source, flags=re.M)
    (work / "adapter_impl.inc").write_text(source)
    binary = work / "test"
    subprocess.run(["g++", "-std=c++17", "-O1", "-g", "-Wall", "-Wextra", "-Werror", "-pthread",
                    "-fsanitize=undefined", "-fno-sanitize-recover=all",
                    "-I", str(ROOT / "components/jarvis_reference"), "-I", str(work),
                    '-DINIT_STOCK=' + ('gate.set_stock_listener(&stock);gate.set_reference_server_id(REFERENCE);' if 'set_stock_listener' in header else ''),
                    str(ROOT / "tests/stock_adapter_test.cpp"), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=20)
