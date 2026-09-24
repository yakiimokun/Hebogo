"""診断SGFに棋譜とAI評価が保存されることを確認する。"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.go_game_app import GoGameApp
from src.move_diagnostics import CandidateEvaluation, MoveAnalysis, MoveRecord
from src.rules import BLACK, WHITE
from src.sgf_dataset import _SGFParser, _main_sequence
from src.sgf_export import build_diagnostic_sgf


class DiagnosticSGFTest(unittest.TestCase):
    def make_analysis(self):
        return MoveAnalysis(
            selected_move=None,
            policy_weight=1.0,
            value_weight=0.001,
            candidates=(
                CandidateEvaluation((3, 3), 0.00284, 0.54, 0.00230),
                CandidateEvaluation(None, 0.00269, 0.39, 0.00230),
            ),
        )

    def test_exports_moves_pass_players_turn_and_analysis(self):
        sgf = build_diagnostic_sgf(
            board_size=19,
            komi=6.5,
            black_name="PolicyValue AI]",
            white_name="Player",
            moves=(
                MoveRecord(BLACK, (15, 3)),
                MoveRecord(WHITE, (3, 15)),
                MoveRecord(BLACK, None, self.make_analysis()),
            ),
            current_turn=WHITE,
        )

        self.assertIn("SZ[19]KM[6.5]", sgf)
        self.assertIn("PB[PolicyValue AI\\]]PW[Player]", sgf)
        self.assertIn(";B[pd];W[dp];B[]C[", sgf)
        self.assertIn("AI selected: PASS", sgf)
        self.assertIn("policy=0.00284", sgf)
        self.assertIn("value=0.39", sgf)
        self.assertIn("Policy weight: 1", sgf)
        self.assertTrue(sgf.endswith(";PL[W]C[Current turn: W])\n"))

        nodes = list(_main_sequence(_SGFParser(sgf).parse_collection()[0]))
        self.assertEqual(nodes[0].properties["SZ"], ["19"])
        self.assertEqual(nodes[1].properties["B"], ["pd"])
        self.assertEqual(nodes[2].properties["W"], ["dp"])
        self.assertEqual(nodes[3].properties["B"], [""])
        self.assertEqual(nodes[4].properties["PL"], ["W"])

    def test_save_dialog_writes_utf8_sgf(self):
        app = GoGameApp.__new__(GoGameApp)
        app.root = MagicMock()
        app.board_size = 9
        app.komi = 7.5
        app.black_type = "Black AI"
        app.white_type = "White AI"
        app.current_turn = WHITE
        app.move_history = [MoveRecord(BLACK, (0, 0))]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "position.sgf"
            with patch("src.go_game_app.filedialog.asksaveasfilename", return_value=str(path)), \
                 patch("src.go_game_app.messagebox.showinfo") as showinfo:
                app.save_diagnostic_sgf()
            content = path.read_text(encoding="utf-8")

        self.assertIn("SZ[9]KM[7.5]PB[Black AI]PW[White AI]", content)
        self.assertIn(";B[aa]", content)
        showinfo.assert_called_once()


if __name__ == "__main__":
    unittest.main()
