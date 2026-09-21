"""Policy Network 学習CLIの契約テスト。"""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from scripts.train_policy import _encode_boards, main
from src.policy_network import PolicyNetwork


class PolicyTrainingTest(unittest.TestCase):
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
