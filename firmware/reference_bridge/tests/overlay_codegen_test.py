"""Generate both real overlays against credential-free hardware fixtures.

Run with the pinned ESPHome Python environment. No compiler, network, device,
microphone, firmware upload, or real API credentials are used by this check.
Only the external-component locator is changed to the local pinned tree.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix="jarvis-overlay-codegen-") as tmp:
        work = Path(tmp)
        common = (ROOT / "voice-pe-common.yaml").read_text()
        remote = """      type: git
      url: https://github.com/mlegnavsky/jarvis
      ref: ${jarvis_reference_source_sha}
      path: firmware/reference_bridge/components"""
        assert common.count(remote) == 1, "unexpected component locator"
        common = common.replace(remote, f"      type: local\n      path: {ROOT / 'components'}")
        (work / "voice-pe-common.yaml").write_text(common)
        for profile in ("legacy", "stock-sendspin"):
            name = f"voice-pe-{profile}.yaml"
            (work / name).write_text((ROOT / name).read_text())

        base = (ROOT / "compile-fixture.yaml").read_text()
        base = re.sub(r"(?ms)^api:\n.*?(?=^logger:)", "api:\n  encryption: {}\n", base)
        base = re.sub(r"(?ms)^external_components:\n.*?(?=^i2c:)", "", base)
        base = base.split("\nsendspin:\n", 1)[0] + "\n"
        for old, new in {
            "physical_speaker": "i2s_audio_speaker",
            "reference_gate": "jarvis_reference_gate",
            "reference_dac": "aic3204_dac",
            "reference_amp": "internal_speaker_amp",
            "normal_mixer": "mixing_speaker",
        }.items():
            base = base.replace(old, new)
        # The overlay must redirect this normal physical output through its gate.
        base = base.replace("output_speaker: jarvis_reference_gate", "output_speaker: i2s_audio_speaker")

        results = {}
        for profile in ("legacy", "stock-sendspin"):
            build = work / f"build-{profile}"
            fixture = base.replace("build_path: /tmp/jarvis-reference-build", f"build_path: {build}")
            fixture += f"packages:\n  overlay: !include voice-pe-{profile}.yaml\n"
            if profile == "stock-sendspin":
                fixture += """sendspin:
  id: sendspin_hub
media_source:
  - platform: sendspin
    id: sendspin_media_source
    codecs: [FLAC, PCM]
    fixed_delay: 480us
"""
            config = work / f"fixture-{profile}.yaml"
            config.write_text(fixture)
            result = subprocess.run([sys.executable, "-m", "esphome", "compile", "--only-generate", str(config)],
                                    capture_output=True, text=True)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            cpp = (build / "src/main.cpp").read_text()
            required = [
                "mixing_speaker->set_output_speaker(jarvis_reference_gate);",
                "mixing_speaker->set_output_bits_per_sample(16);",
                "jarvis_reference_gate->set_output_speaker(i2s_audio_speaker);",
                "jarvis_reference_gate->set_dac_id(aic3204_dac);",
                "jarvis_reference_gate->set_amplifier_id(internal_speaker_amp);",
                "sendspin_hub->set_listener(jarvis_reference_gate);",
                "sendspin_hub->set_unpaired_access_enabled(false);",
            ]
            for statement in required:
                assert statement in cpp, statement
            reference_at = cpp.index("sendspin_hub->set_listener(jarvis_reference_gate);")
            stock_at = cpp.find("sendspin_hub->set_listener(sendspin_media_source);")
            assert stock_at < reference_at
            assert (stock_at >= 0) == (profile == "stock-sendspin")
            for action in ("status", "arm", "cancel", "pairing"):
                assert f'"jarvis_reference_{action}"' in cpp, action
            results[profile] = {"passed": True,
                "fixture_sha256": sha(fixture.encode()), "generated_cpp_sha256": sha(cpp.encode()),
                "stock_listener_before_reference": stock_at >= 0 and stock_at < reference_at,
                "all_normal_output_through_gate": True}
        print(json.dumps({"profiles": results, "scope": "real overlay code generation against minimal hardware fixtures; no installed device package"}, indent=2))


if __name__ == "__main__":
    main()
