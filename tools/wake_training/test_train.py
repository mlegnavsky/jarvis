import unittest
from train import target_phrases, safe_members, model_directory
from pathlib import Path
from tempfile import TemporaryDirectory


class TrainingInputTests(unittest.TestCase):
    def test_upstream_training_directory_is_not_the_existing_artifact_directory(self):
        with TemporaryDirectory() as temporary:
            artifact = Path(temporary) / 'candidate'
            artifact.mkdir()
            model = model_directory(artifact)
            self.assertFalse(model.exists())
            self.assertTrue(model.is_relative_to(artifact))

    def test_all_requested_commands_have_czech_targets(self):
        self.assertEqual(target_phrases('rozsvit'), ['rozsviť'])
        self.assertEqual(target_phrases('zhasni'), ['zhasni'])
        self.assertEqual(target_phrases('zamkni'), ['zamkni'])
        self.assertEqual(target_phrases('odemkni'), ['odemkni'])

    def test_jarvis_includes_existing_czech_address(self):
        self.assertEqual(target_phrases('jarvis'), ['Jarvis', 'Jarvisi'])

    def test_unrecognized_input_cannot_become_a_path_or_shell_command(self):
        for value in ['../zhasni', 'zhasni;id', '', None]:
            with self.assertRaises(ValueError):
                target_phrases(value)

    def test_dataset_zip_paths_stay_inside_destination(self):
        self.assertEqual(safe_members(['speech/train/a.npy']), ['speech/train/a.npy'])
        for name in ['../outside', '/tmp/outside', 'speech/../../outside', 'speech\\..\\outside']:
            with self.assertRaises(ValueError):
                safe_members([name])
