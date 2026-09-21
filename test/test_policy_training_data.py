import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.policy_training_data import load_policy_splits
from src.sgf_dataset import samples_from_sgf


class PolicyTrainingDataTest(unittest.TestCase):
    def _write_game(self, root, name, body, size=9):
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"(;GM[1]SZ[{size}]RE[B+R]{body})", encoding="utf-8")
        return path

    def test_deterministic_disjoint_split_uses_whole_games(self):
        with tempfile.TemporaryDirectory() as directory:
            for index in range(5):
                self._write_game(
                    directory,
                    f"nested/game_{index}.SGF",
                    f";B[{chr(ord('a') + index)}a];W[]",
                )
            with patch(
                "src.policy_training_data.samples_from_sgf", wraps=samples_from_sgf
            ) as parse:
                split = load_policy_splits(Path(directory), 9, 0.4, seed=7)
            again = load_policy_splits(Path(directory), 9, 0.4, seed=7)

        self.assertEqual(parse.call_count, 5)
        self.assertEqual(split.train_files, again.train_files)
        self.assertEqual(split.validation_files, again.validation_files)
        self.assertEqual(len(split.train_files), 3)
        self.assertEqual(len(split.validation_files), 2)
        self.assertFalse(set(split.train_files) & set(split.validation_files))
        self.assertEqual(split.train_boards.shape, (6, 9, 9))
        self.assertEqual(split.validation_boards.shape, (4, 9, 9))
        self.assertEqual(split.train_boards.dtype, np.int8)
        self.assertEqual(split.train_moves.dtype, np.int64)
        self.assertEqual(split.validation_moves.dtype, np.int64)
        # 各棋譜の 2 サンプルが同じ側に入り、パスも正解手として残る。
        self.assertEqual(split.train_moves.tolist()[1::2], [81] * 3)
        self.assertEqual(split.validation_moves.tolist()[1::2], [81] * 2)
        train_points = set(split.train_moves.tolist()[0::2])
        validation_points = set(split.validation_moves.tolist()[0::2])
        self.assertFalse(train_points & validation_points)

    def test_board_is_normalized_for_player_to_move(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_game(directory, "game.sgf", ";B[aa];W[ba];B[]")
            split = load_policy_splits(Path(directory), 9, 0)

        self.assertEqual(split.train_moves.tolist(), [0, 1, 81])
        self.assertEqual(split.train_boards[0, 0, 0], 0)
        self.assertEqual(split.train_boards[1, 0, 0], -1)
        self.assertEqual(split.train_boards[2, 0, 0], 1)
        self.assertEqual(split.train_boards[2, 0, 1], -1)
        self.assertEqual(split.validation_boards.shape, (0, 9, 9))
        self.assertEqual(split.validation_moves.shape, (0,))
        self.assertEqual(split.validation_files, ())

    def test_one_file_requires_zero_validation_fraction(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_game(directory, "game.sgf", ";B[aa]")
            with self.assertRaisesRegex(ValueError, "2 件以上"):
                load_policy_splits(Path(directory), 9, 0.2)

    def test_filters_other_size_and_reports_malformed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_game(directory, "good.sgf", ";B[aa]")
            self._write_game(directory, "other.sgf", ";B[aa]", size=13)
            (Path(directory) / "bad.sgf").write_text("(;RE[?];B[aa])", encoding="utf-8")
            split = load_policy_splits(Path(directory), 9, 0)

        self.assertEqual(split.train_files, ("good.sgf",))
        self.assertEqual(len(split.skipped_files), 1)
        self.assertEqual(split.skipped_files[0]["file"], "bad.sgf")
        self.assertTrue(split.skipped_files[0]["reason"])

    def test_rejects_invalid_arguments_and_missing_matching_games(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_game(directory, "other.sgf", ";B[aa]", size=13)
            with self.assertRaises(ValueError):
                load_policy_splits(Path(directory), 7)
            with self.assertRaises(ValueError):
                load_policy_splits(Path(directory), 9, -0.1)
            with self.assertRaises(ValueError):
                load_policy_splits(Path(directory), 9, 1)
            with self.assertRaisesRegex(ValueError, "有効な SGF"):
                load_policy_splits(Path(directory), 9)
            with self.assertRaises(FileNotFoundError):
                load_policy_splits(Path(directory) / "missing", 9)


if __name__ == "__main__":
    unittest.main()
