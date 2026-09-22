"""Value Network の教師ラベルと棋譜単位分割を検証する。"""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.value_training_data import load_value_splits


class ValueTrainingDataTest(unittest.TestCase):
    def _write_game(self, root, name, result="B+R", size=9):
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"(;GM[1]SZ[{size}]RE[{result}];B[aa];W[ba];B[])\n",
            encoding="utf-8",
        )
        return path

    def test_labels_are_from_player_to_move_perspective(self):
        for result, expected in (("B+R", [1, -1, 1]), ("W+1.5", [-1, 1, -1]), ("0", [0, 0, 0])):
            with self.subTest(result=result), tempfile.TemporaryDirectory() as directory:
                self._write_game(directory, "game.sgf", result=result)
                split = load_value_splits(Path(directory), 9, 0)

                self.assertEqual(split.train_values.tolist(), expected)
                self.assertEqual(split.train_boards.shape, (3, 9, 9))
                self.assertEqual(split.train_boards.dtype, np.int8)
                self.assertEqual(split.train_boards[1, 0, 0], -1)
                self.assertEqual(split.train_boards[2, 0, 0], 1)
                self.assertEqual(split.train_boards[2, 0, 1], -1)
                self.assertEqual(split.validation_boards.shape, (0, 9, 9))
                self.assertEqual(split.validation_values.shape, (0,))

    def test_split_is_deterministic_and_keeps_whole_games(self):
        with tempfile.TemporaryDirectory() as directory:
            for index in range(5):
                self._write_game(
                    directory,
                    f"nested/game_{index}.sgf",
                    result="B+R" if index % 2 == 0 else "W+R",
                )
            split = load_value_splits(Path(directory), 9, 0.4, seed=7)
            again = load_value_splits(Path(directory), 9, 0.4, seed=7)

        self.assertEqual(split.train_files, again.train_files)
        self.assertEqual(split.validation_files, again.validation_files)
        self.assertEqual(len(split.train_files), 3)
        self.assertEqual(len(split.validation_files), 2)
        self.assertFalse(set(split.train_files) & set(split.validation_files))
        self.assertEqual(split.train_boards.shape, (9, 9, 9))
        self.assertEqual(split.validation_boards.shape, (6, 9, 9))
        for values in (split.train_values, split.validation_values):
            self.assertEqual(len(values) % 3, 0)
            for offset in range(0, len(values), 3):
                self.assertEqual(values[offset], values[offset + 2])
                self.assertEqual(values[offset], -values[offset + 1])

    def test_filters_other_sizes_and_reports_invalid_sgf(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_game(directory, "valid.sgf")
            self._write_game(directory, "other.sgf", size=13)
            (Path(directory) / "bad.sgf").write_text("(;RE[?];B[aa])", encoding="utf-8")
            split = load_value_splits(Path(directory), 9, 0)

        self.assertEqual(split.train_files, ("valid.sgf",))
        self.assertEqual(len(split.skipped_files), 1)
        self.assertEqual(split.skipped_files[0]["file"], "bad.sgf")

    def test_rejects_invalid_arguments_and_missing_games(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_game(directory, "other.sgf", size=13)
            with self.assertRaises(ValueError):
                load_value_splits(Path(directory), 7)
            with self.assertRaises(ValueError):
                load_value_splits(Path(directory), 9, -0.1)
            with self.assertRaises(ValueError):
                load_value_splits(Path(directory), 9, 1)
            with self.assertRaisesRegex(ValueError, "有効な SGF"):
                load_value_splits(Path(directory), 9)
            with self.assertRaises(FileNotFoundError):
                load_value_splits(Path(directory) / "missing", 9)

        with tempfile.TemporaryDirectory() as directory:
            self._write_game(directory, "only.sgf")
            with self.assertRaisesRegex(ValueError, "2 件以上"):
                load_value_splits(Path(directory), 9, 0.2)


if __name__ == "__main__":
    unittest.main()
