"""棋譜の追加後も検証データが固定されることを検証する。"""

import json
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np

from src.policy_training_data import load_policy_splits
from src.value_training_data import load_value_splits


class FixedTrainingSplitTest(unittest.TestCase):
    """Policy・Value 間で共有する分割履歴を検証する。"""

    def setUp(self):
        """異なる内容の9路棋譜を5局用意する。"""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for i in range(5):
            self._game(f"game_{i}.sgf", chr(97 + i))
        self.manifest = self.root / "split_9x9.json"

    def _game(self, name, coordinate="h", size=9):
        path = self.root / name
        path.write_text(f"(;GM[1]SZ[{size}]RE[B+R];B[{coordinate}a];W[])", encoding="utf-8")

    def test_initial_split_matches_previous_algorithm_and_additions_are_training(self):
        """従来と同じ初回分割を保存し、追加後も検証の内容と順序を保つ。"""
        before = load_policy_splits(self.root, 9, 0.4, 7)
        expected = [f"game_{i}.sgf" for i in range(5)]
        random.Random(7).shuffle(expected)
        self.assertEqual(before.validation_files, tuple(expected[:2]))
        self.assertEqual(before.train_files, tuple(expected[2:]))
        original_validation = json.loads(self.manifest.read_text())["validation_files"]
        self._game("aaa_new.sgf")
        after = load_policy_splits(self.root, 9, 0.8, 99)
        value = load_value_splits(self.root, 9, 0.2, 42)
        self.assertEqual(after.train_files, before.train_files + ("aaa_new.sgf",))
        self.assertEqual(after.validation_files, before.validation_files)
        np.testing.assert_array_equal(after.validation_boards, before.validation_boards)
        np.testing.assert_array_equal(after.validation_moves, before.validation_moves)
        self.assertEqual(value.validation_files, after.validation_files)
        self.assertEqual(value.train_files, after.train_files)
        self.assertEqual(json.loads(self.manifest.read_text())["validation_files"], original_validation)

    def test_missing_changed_or_invalid_validation_is_not_silently_replaced(self):
        """検証棋譜を削除・編集・破損した場合に再分割せず停止する。"""
        split = load_policy_splits(self.root, 9)
        path = self.root / split.validation_files[0]
        original = path.read_bytes()
        manifest = self.manifest.read_bytes()
        for content in (None, original.replace(b"B+R", b"W+R"), b"broken"):
            if content is None:
                path.unlink()
            else:
                path.write_bytes(content)
            with self.assertRaisesRegex(ValueError, "検証棋譜"):
                load_policy_splits(self.root, 9)
            self.assertEqual(self.manifest.read_bytes(), manifest)
            path.write_bytes(original)

    def test_added_validation_copy_is_rejected(self):
        """別名で追加された検証棋譜を訓練側へ混入させない。"""
        split = load_policy_splits(self.root, 9)
        (self.root / "copy.sgf").write_bytes((self.root / split.validation_files[0]).read_bytes())
        with self.assertRaisesRegex(ValueError, "同一内容"):
            load_value_splits(self.root, 9)

    def test_sizes_have_independent_manifests(self):
        """異なる盤面サイズの分割履歴を分離する。"""
        nine = load_policy_splits(self.root, 9)
        self._game("thirteen_a.sgf", "a", 13)
        self._game("thirteen_b.sgf", "b", 13)
        thirteen = load_value_splits(self.root, 13)
        self.assertEqual(len(thirteen.validation_files), 1)
        self.assertTrue((self.root / "split_13x13.json").exists())
        self.assertEqual(load_policy_splits(self.root, 9).validation_files, nine.validation_files)

    def test_disabled_validation_does_not_create_or_override_manifest(self):
        """動作確認の検証無効化で分割を固定せず、既存の検証は訓練へ回さない。"""
        self.assertEqual(load_policy_splits(self.root, 9, 0).validation_files, ())
        self.assertFalse(self.manifest.exists())
        load_policy_splits(self.root, 9)
        original = self.manifest.read_bytes()
        with self.assertRaisesRegex(ValueError, "保存済み"):
            load_value_splits(self.root, 9, 0)
        self.assertEqual(self.manifest.read_bytes(), original)

    def test_corrupt_manifest_is_not_overwritten(self):
        """分割履歴が壊れていた場合は新しい分割で上書きしない。"""
        for content in ("broken", "[]", '{"version": 1, "board_size": 9}'):
            self.manifest.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "分割ファイル"):
                load_policy_splits(self.root, 9)
            self.assertEqual(self.manifest.read_text(), content)


if __name__ == "__main__":
    unittest.main()
