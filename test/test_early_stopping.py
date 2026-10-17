"""Policy・Value の早期終了と最良モデル保存を検証する。"""

from contextlib import redirect_stdout, redirect_stderr
import importlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class EarlyStoppingTest(unittest.TestCase):
    """既知のloss系列を使い、停止境界と改善時のリセットを確認する。"""

    def _run(self, kind, losses, patience=None, validation=True):
        module = importlib.import_module(f"scripts.train_{kind}")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, move in (("one", "aa"), ("two", "cc")):
                (root / f"{name}.sgf").write_text(f"(;GM[1]SZ[9]RE[B+R];B[{move}];W[bb])")
            args = ["--input", str(root), "--output", str(root / "model.pt"),
                    "--board-size", "9", "--epochs", str(len(losses)), "--device", "cpu"]
            if patience is not None:
                args += ["--patience", str(patience)]
            if not validation:
                args += ["--validation-fraction", "0"]
            sequence = []
            for loss in losses:
                sequence.append((1.0, 0.1))
                if validation:
                    sequence.append((loss, 0.1))
            out, err = io.StringIO(), io.StringIO()
            saved_after = []
            with patch.object(module, "_epoch", side_effect=sequence) as epoch, \
                    patch.object(module.torch, "save", side_effect=lambda *a: saved_after.append(epoch.call_count)), \
                    redirect_stdout(out), redirect_stderr(err):
                status = module.main(args)
            return status, out.getvalue(), err.getvalue(), epoch.call_count, saved_after

    def test_default_stops_after_five_non_improvements(self):
        """既定は5回の停滞で終了し、それ以降の重みを保存しない。"""
        for kind in ("policy", "value"):
            with self.subTest(kind=kind):
                status, out, err, calls, saves = self._run(kind, [4, 3, 3, 4, 4, 4, 4, 2])
                self.assertEqual(status, 0, err)
                self.assertEqual(calls, 14)
                self.assertEqual(saves, [2, 4])
                self.assertIn("最良: epoch 2", out)
                self.assertIn("5エポック連続", out)

    def test_improvement_resets_counter_and_equal_loss_does_not(self):
        """改善したらカウンターをリセットし、同値は改善に含めない。"""
        for kind in ("policy", "value"):
            with self.subTest(kind=kind):
                status, out, err, calls, saves = self._run(kind, [4, 4, 3, 3, 3, 2], 2)
                self.assertEqual(status, 0, err)
                self.assertEqual(calls, 10)
                self.assertEqual(saves, [2, 6])
                self.assertIn("最良: epoch 3", out)

    def test_disabled_stopping_and_disabled_validation_run_all_epochs(self):
        """早期終了の無効化や検証なしの場合は指定回数を実行する。"""
        for kind in ("policy", "value"):
            for validation in (True, False):
                with self.subTest(kind=kind, validation=validation):
                    status, out, err, calls, saves = self._run(kind, [3] * 8, 0 if validation else 1, validation)
                    self.assertEqual(status, 0, err)
                    self.assertEqual(calls, 16 if validation else 8)
                    self.assertEqual(len(saves), 1 if validation else 8)
                    self.assertNotIn("早期終了:", out)

    def test_nonfinite_loss_stops_with_error_and_preserves_best(self):
        """非有限lossは早期終了扱いにせずエラーとし、最良モデルを上書きしない。"""
        for kind in ("policy", "value"):
            with self.subTest(kind=kind):
                status, _, err, calls, saves = self._run(kind, [3, float("nan"), 2])
                self.assertEqual(status, 1)
                self.assertEqual(calls, 4)
                self.assertEqual(saves, [2])
                self.assertIn("有限値", err)

    def test_rejects_negative_patience(self):
        """負の待機エポック数は引数エラーにする。"""
        for kind in ("policy", "value"):
            module = importlib.import_module(f"scripts.train_{kind}")
            with self.subTest(kind=kind), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                module.main(["--patience", "-1"])
            self.assertEqual(caught.exception.code, 2)
