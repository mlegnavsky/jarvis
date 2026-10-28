"""Train experimental Czech microWakeWord candidates, never deploy firmware.

Based on kahrendt/microWakeWord's basic training notebook. Synthetic benchmarks
are not household acceptance tests. No credentials or household recordings are
used. Dataset licenses must be retained; these candidates are for personal use.
"""
import argparse
import hashlib
import json
import random
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

TARGETS = {'rozsvit': ['rozsviť'], 'zhasni': ['zhasni'], 'zamkni': ['zamkni'],
           'odemkni': ['odemkni'], 'jarvis': ['Jarvis', 'Jarvisi']}
DATASET_REVISION = '0da95f94302ca2f4aae3b18fc6560fa6d2bba3d1'
VOICE_REVISION = '5041a7a49ae5b3a0f30e6837769eb03fdbb231bd'


def target_phrases(target):
    if not isinstance(target, str) or target not in TARGETS:
        raise ValueError('unknown_target')
    return list(TARGETS[target])


def safe_members(names):
    for name in names:
        if '\\' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
            raise ValueError('unsafe_dataset_archive')
    return names


def model_directory(artifact_directory):
    """Upstream creates this itself and refuses an already-existing folder."""
    return Path(artifact_directory) / 'model'


def download(url, path, expected=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temp = path.with_suffix(path.suffix + '.part')
        with urllib.request.urlopen(url, timeout=120) as response, temp.open('wb') as out:
            while block := response.read(1024 * 1024):
                out.write(block)
        temp.replace(path)
    with path.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if expected and digest != expected:
        raise ValueError('download_checksum_mismatch:' + path.name)
    return digest


def negatives(root):
    api = 'https://huggingface.co/api/datasets/kahrendt/microwakeword'
    revision = DATASET_REVISION
    with urllib.request.urlopen(api + '/tree/' + revision, timeout=60) as response:
        listing = {row['path']: row for row in json.load(response)}
    receipts = {'revision': revision, 'files': {}}
    for name in ['dinner_party.zip', 'dinner_party_eval.zip', 'no_speech.zip', 'speech.zip']:
        path = root / name
        expected = listing[name]['lfs']['oid']
        digest = download('https://huggingface.co/datasets/kahrendt/microwakeword/resolve/' + revision + '/' + name, path, expected)
        with zipfile.ZipFile(path) as archive:
            safe_members(archive.namelist())
            archive.extractall(root)
        receipts['files'][name] = digest
        path.unlink()
    return receipts


def samples(target, root, count):
    import numpy as np
    from piper import PiperVoice, SynthesisConfig
    from scipy.signal import resample_poly
    from scipy.io import wavfile
    from math import gcd
    rng = random.Random(28)
    receipts = {}
    for speaker in ['jirka', 'kasandra']:
        model_name = 'cs_CZ-' + speaker + '-medium.onnx'
        model = root / 'voices' / model_name
        base = 'https://huggingface.co/rhasspy/piper-voices/resolve/' + VOICE_REVISION + '/cs/cs_CZ/' + speaker + '/medium/'
        receipts[model_name] = download(base + model_name, model)
        receipts[model_name + '.json'] = download(base + model_name + '.json', Path(str(model) + '.json'))
        voice = PiperVoice.load(str(model))
        for label in TARGETS:
            out = root / ('positive' if label == target else 'confusers')
            out.mkdir(exist_ok=True)
            number = count if label == target else max(20, count // 5)
            for index in range(number):
                text = rng.choice(target_phrases(label))
                config = SynthesisConfig(length_scale=rng.uniform(.8, 1.25),
                                         noise_scale=rng.uniform(.45, .9), noise_w_scale=rng.uniform(.6, 1.0))
                chunks = list(voice.synthesize(text, config))
                if not chunks:
                    raise ValueError('empty_synthesis')
                rate = chunks[0].sample_rate
                pcm = np.frombuffer(b''.join(c.audio_int16_bytes for c in chunks), dtype='<i2').astype(np.float32)
                divisor = gcd(rate, 16000)
                pcm = resample_poly(pcm, 16000 // divisor, rate // divisor)
                wavfile.write(out / f'{speaker}-{label}-{index}.wav', 16000, np.clip(pcm, -32768, 32767).astype(np.int16))
        print('Synthesis complete:', speaker, target, flush=True)
    return receipts


def features(folder, destination):
    from microwakeword.audio.clips import Clips
    from microwakeword.audio.augmentation import Augmentation
    from microwakeword.audio.spectrograms import SpectrogramGeneration
    from mmap_ninja.ragged import RaggedMmap
    clips = Clips(input_directory=str(folder), file_pattern='*.wav', max_clip_duration_s=None,
                  remove_silence=False, random_split_seed=28, split_count=.1)
    augmenter = Augmentation(augmentation_duration_s=3.2,
        augmentation_probabilities={'SevenBandParametricEQ': .1, 'TanhDistortion': .1,
        'PitchShift': .1, 'BandStopFilter': .1, 'AddColorNoise': .5, 'Gain': 1.0},
        impulse_paths=[], background_paths=[], min_jitter_s=.195, max_jitter_s=.205)
    for split, source in [('training', 'train'), ('validation', 'validation'), ('testing', 'test')]:
        dest = destination / split / 'wakeword_mmap'
        dest.parent.mkdir(parents=True, exist_ok=True)
        generator = SpectrogramGeneration(clips, augmenter, step_ms=10,
                                         slide_frames=1 if split == 'testing' else 10)
        RaggedMmap.from_generator(out_dir=str(dest), sample_generator=generator.spectrogram_generator(
            split=source, repeat=1), batch_size=100, verbose=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target', choices=list(TARGETS))
    parser.add_argument('--samples-per-voice', type=int, default=300)
    parser.add_argument('--steps', type=int, default=10000)
    args = parser.parse_args()
    if not 100 <= args.samples_per_voice <= 2000 or not 1000 <= args.steps <= 50000:
        parser.error('invalid training bounds')
    import yaml
    root = Path('wake-training-work').resolve()
    root.mkdir(exist_ok=True)
    output = Path('wake-training-output') / args.target
    output.mkdir(parents=True, exist_ok=True)
    (output / 'NOT_DEPLOYABLE.txt').write_text('Experimental synthetic-only candidate. No household accuracy, false-activation, firmware or lock authorization acceptance. Never auto-flash.\n')
    receipt = {'target': args.target, 'phrases': target_phrases(args.target),
               'deployable': False, 'evaluation_scope': 'two synthetic Czech voices only'}
    receipt['voices'] = samples(args.target, root, args.samples_per_voice)
    features(root / 'positive', root / 'positive_features')
    features(root / 'confusers', root / 'confuser_features')
    receipt['negative_dataset'] = negatives(root / 'negative_datasets')
    (output / 'provenance.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    feature_sets = []
    for path, weight, truth, strategy in [
        (root / 'positive_features', 2, True, 'truncate_start'),
        (root / 'confuser_features', 5, False, 'truncate_start'),
        *[(root / 'negative_datasets' / name, weight, False, strategy) for name, weight, strategy in [
            ('speech', 10, 'random'), ('dinner_party', 10, 'random'), ('no_speech', 5, 'random'),
            ('dinner_party_eval', 0, 'split')]]]:
        feature_sets.append(dict(features_dir=str(path), sampling_weight=weight, penalty_weight=1.,
                                 truth=truth, truncation_strategy=strategy, type='mmap'))
    config = dict(window_step_ms=10, train_dir=str(model_directory(output).resolve()), features=feature_sets,
        training_steps=[args.steps], positive_class_weight=[1], negative_class_weight=[20],
        learning_rates=[.001], batch_size=128, time_mask_max_size=[0], time_mask_count=[0],
        freq_mask_max_size=[0], freq_mask_count=[0], eval_step_interval=500, clip_duration_ms=1500,
        target_minimization=.2, minimization_metric='ambient_false_positives_per_hour',
        maximization_metric='average_viable_recall')
    config_file = output / 'training_parameters.yaml'
    config_file.write_text(yaml.safe_dump(config))
    subprocess.run([sys.executable, '-m', 'microwakeword.model_train_eval',
        '--training_config', str(config_file), '--train', '1', '--restore_checkpoint', '0',
        '--test_tflite_streaming_quantized', '1', '--use_weights', 'best_weights', 'mixednet',
        '--pointwise_filters', '64,64,64,64', '--repeat_in_block', '1,1,1,1',
        '--mixconv_kernel_sizes', '[5], [7,11], [9,15], [23]', '--residual_connection', '0,0,0,0',
        '--first_conv_filters', '32', '--first_conv_kernel_size', '5', '--stride', '3'], check=True)
    model = model_directory(output) / 'tflite_stream_state_internal_quant/stream_state_internal_quant.tflite'
    if not model.is_file():
        raise RuntimeError('training_did_not_produce_model')
    print(json.dumps({'candidate': str(model), 'deployable': False}), flush=True)


if __name__ == '__main__':
    main()
