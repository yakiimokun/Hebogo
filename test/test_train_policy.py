"""Policy Network 学習CLIの契約テスト。"""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from scripts.train_policy import _encode_boards, _loader, _transform_sample, main
from src.policy_network import PolicyNetwork


class PolicyTrainingTest(unittest.TestCase):
    def test_all_symmetries_move_stones_and_target_together(self):
        """9・13・19路の全対称変換で石・正解手・パスの対応を保つ。"""
        for size in (9, 13, 19):
            board = torch.zeros(3, size, size)
            board[0] = 1
            board[0, 2, 1] = 0
            board[1, 2, 1] = 1
            board[0, 0, 0] = 0
            board[2, 0, 0] = 1
            original = board.clone()
            # 元の (x, y)=(1, 2) の各変換後の座標。
            points = [(1, 2), (2, size - 2), (size - 2, size - 3), (size - 3, 1),
                      (size - 2, 2), (size - 3, size - 2), (1, size - 3), (2, 1)]
            variants = []
            for symmetry, (x, y) in enumerate(points):
                with self.subTest(size=size, symmetry=symmetry):
                    transformed, target = _transform_sample(board, torch.tensor(2 * size + 1), symmetry)
                    self.assertEqual(int(target), y * size + x)
                    self.assertEqual(transformed[:, y, x].tolist(), [0, 1, 0])
                    self.assertEqual(transformed[2].sum().item(), 1)
                    self.assertTrue(torch.equal(transformed.sum(0), torch.ones(size, size)))
                    self.assertEqual(transformed.shape, board.shape)
                    self.assertEqual(target.dtype, torch.int64)
                    _, target_pass = _transform_sample(board, torch.tensor(size * size), symmetry)
                    self.assertEqual(int(target_pass), size * size)
                    variants.append(transformed.numpy().tobytes())
            self.assertEqual(len(set(variants)), 8)
            self.assertTrue(torch.equal(board, original))

    def test_loader_augmentation_is_reproducible_and_validation_unchanged(self):
        """同じ seed の変換を再現し、無効時は元の盤面と正解手を返す。"""
        boards = np.zeros((32, 9, 9), dtype=np.int8)
        boards[:, 2, 1] = 1
        moves = np.full(32, 19, dtype=np.int64)
        first = _loader(boards, moves, 32, True, 42, augment=True)
        second = _loader(boards, moves, 32, True, 42, augment=True)
        batches = []
        for _ in range(2):
            batch, target = next(iter(first))
            other_batch, other_target = next(iter(second))
            self.assertTrue(torch.equal(batch, other_batch))
            self.assertTrue(torch.equal(target, other_target))
            self.assertEqual(batch.shape, (32, 3, 9, 9))
            self.assertTrue(torch.equal(batch[:, 1].flatten(1).argmax(1), target))
            batches.append(target)
        self.assertFalse(torch.equal(batches[0], batches[1]))
        validation = _loader(boards, moves, 32, False, 42)
        for _ in range(2):
            batch, target = next(iter(validation))
            self.assertTrue(torch.equal(batch, _encode_boards(boards)))
            self.assertEqual(target.tolist(), moves.tolist())
        self.assertTrue(np.all(boards[:, 2, 1] == 1))

    def test_cli_augments_only_training_and_supports_opt_out(self):
        """CLI は訓練だけ拡張し、無効化しても検証を継続する。"""
        self._sgf("first.sgf", "aa")
        self._sgf("second.sgf", "cc")
        for extra, expected in (((), True), (("--no-augment",), False)):
            with patch("scripts.train_policy._loader", wraps=_loader) as loader:
                status, output, errors = self._run(*extra)
            self.assertEqual(status, 0, errors)
            self.assertEqual(loader.call_args_list[0].kwargs["augment"], expected)
            self.assertFalse(loader.call_args_list[1].kwargs.get("augment", False))
            self.assertIn("validation loss=", output)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.input_dir = self.folder / "sgf"
        self.input_dir.mkdir()
        self.output = self.folder / "model.pt"

    def _sgf(self, name: str, first_move: str):
        (self.input_dir / name).write_text(
            f"(;GM[1]SZ[9]RE[B+R];B[{first_move}];W[bb])",
            encoding="utf-8",
        )

    def _run(self, *extra: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = [
            "--input", str(self.input_dir),
            "--board-size", "9",
            "--output", str(self.output),
            "--epochs", "1",
            "--batch-size", "2",
            "--device", "cpu",
            *extra,
        ]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(argv)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_channel_order_matches_contract(self):
        boards = np.array([[[0, 1], [-1, 0]]], dtype=np.int8)

        encoded = _encode_boards(boards)

        self.assertEqual(encoded.shape, (1, 3, 2, 2))
        self.assertEqual(encoded.dtype, torch.float32)
        self.assertEqual(encoded[0, :, 0, 0].tolist(), [1, 0, 0])
        self.assertEqual(encoded[0, :, 0, 1].tolist(), [0, 1, 0])
        self.assertEqual(encoded[0, :, 1, 0].tolist(), [0, 0, 1])

    def test_two_games_train_and_save_compatible_state_dict(self):
        self._sgf("first.sgf", "aa")
        self._sgf("second.sgf", "cc")

        status, output, errors = self._run()

        self.assertEqual(status, 0, errors)
        self.assertIn("検証: 1棋譜", output)
        self.assertIn("validation loss=", output)
        self.assertIn("top-1=", output)
        model = PolicyNetwork(9)
        model.load_state_dict(torch.load(self.output, map_location="cpu", weights_only=True))
        self.assertEqual(model(torch.zeros(1, 3, 9, 9)).shape, (1, 82))

    def test_single_game_requires_explicitly_disabled_validation(self):
        self._sgf("only.sgf", "aa")

        status, _, errors = self._run()

        self.assertEqual(status, 1)
        self.assertIn("2 件以上", errors)
        self.assertIn("--validation-fraction 0", errors)
        self.assertFalse(self.output.exists())

        status, output, errors = self._run("--validation-fraction", "0")
        self.assertEqual(status, 0, errors)
        self.assertIn("検証: 0棋譜", output)
        self.assertNotIn("validation loss=", output)
        self.assertTrue(self.output.exists())

    def test_rejects_invalid_training_options(self):
        for options in (
            ("--epochs", "0"),
            ("--batch-size", "0"),
            ("--learning-rate", "0"),
            ("--validation-fraction", "1"),
        ):
            with self.subTest(options=options), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    main(list(options))
                self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
