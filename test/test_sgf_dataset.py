import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.sgf_dataset import SGFError, generate_datasets, samples_from_sgf


class SGFDatasetTest(unittest.TestCase):
    def _write_sgf(self, directory, name, content):
        path = Path(directory) / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_generates_normalized_policy_and_value_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_sgf(
                directory,
                "game.sgf",
                "(;GM[1]FF[4]SZ[9]RE[B+R];B[aa];W[ba];B[])"
            )

            board_size, samples = samples_from_sgf(path)

        self.assertEqual(board_size, 9)
        self.assertEqual([sample.move for sample in samples], [0, 1, 81])
        self.assertEqual([sample.value for sample in samples], [1, -1, 1])
        self.assertEqual(samples[1].board[0, 0], -1)

    def test_uses_only_first_variation_and_applies_setup_stones(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_sgf(
                directory,
                "variation.sgf",
                "(;GM[1]SZ[9]RE[W+1.5]AB[aa:ab]PL[W];W[cc](;B[dd])(;B[ee]))"
            )

            _, samples = samples_from_sgf(path)

        self.assertEqual([sample.move for sample in samples], [20, 30])
        self.assertEqual(samples[0].board[0, 0], -1)
        self.assertEqual(samples[0].board[1, 0], -1)

    def test_generates_npz_and_manifest_while_skipping_invalid_game(self):
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            self._write_sgf(
                input_directory,
                "valid.sgf",
                "(;GM[1]SZ[9]RE[W+R];B[aa];W[bb])",
            )
            self._write_sgf(
                input_directory,
                "invalid.sgf",
                "(;GM[1]SZ[9]RE[?];B[aa])",
            )

            manifest = generate_datasets(Path(input_directory), Path(output_directory))
            dataset = np.load(Path(output_directory) / "train_9x9.npz")

            self.assertEqual(dataset["boards"].shape, (2, 9, 9))
            self.assertEqual(dataset["moves"].tolist(), [0, 10])
            self.assertEqual(dataset["values"].tolist(), [-1, 1])
            self.assertEqual(len(manifest["processed_files"]), 1)
            self.assertEqual(len(manifest["skipped_files"]), 1)
            self.assertTrue((Path(output_directory) / "manifest.json").is_file())

    def test_rejects_unsupported_board_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_sgf(
                directory,
                "game.sgf",
                "(;GM[1]SZ[7]RE[B+R];B[aa])",
            )
            with self.assertRaises(SGFError):
                samples_from_sgf(path)


if __name__ == "__main__":
    unittest.main()
