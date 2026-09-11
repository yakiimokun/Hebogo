import unittest

from src.rules import (
    BLACK, KO, OCCUPIED, SUICIDE, WHITE,
    calculate_score_japanese, play_move,
)


class TestRules(unittest.TestCase):
    def test_occupied_point_is_forbidden(self):
        board = [[0] * 3 for _ in range(3)]
        board[1][1] = BLACK
        result = play_move(board, 1, 1, WHITE)
        self.assertFalse(result.legal)
        self.assertEqual(result.reason, OCCUPIED)

    def test_suicide_is_forbidden(self):
        board = [[0, BLACK, 0], [BLACK, 0, BLACK], [0, BLACK, 0]]
        result = play_move(board, 1, 1, WHITE)
        self.assertFalse(result.legal)
        self.assertEqual(result.reason, SUICIDE)

    def test_capture_makes_move_legal(self):
        board = [[0, BLACK, 0], [BLACK, WHITE, BLACK], [0, 0, 0]]
        result = play_move(board, 1, 2, BLACK)
        self.assertTrue(result.legal)
        self.assertEqual(result.captured, 1)
        self.assertEqual(result.board[1][1], 0)
        self.assertEqual(board[2][1], 0)  # 入力盤面は変更しない

    def test_simple_ko_is_forbidden(self):
        before_capture = [[0] * 5 for _ in range(5)]
        before_capture[1][2] = BLACK
        before_capture[2][1] = BLACK
        before_capture[3][2] = BLACK
        before_capture[2][2] = WHITE
        before_capture[1][3] = WHITE
        before_capture[2][4] = WHITE
        before_capture[3][3] = WHITE
        capture = play_move(before_capture, 3, 2, BLACK)
        self.assertTrue(capture.legal)
        self.assertEqual(capture.captured, 1)

        recapture = play_move(capture.board, 2, 2, WHITE, previous_board=before_capture)
        self.assertFalse(recapture.legal)
        self.assertEqual(recapture.reason, KO)

    def test_japanese_score_counts_territory_captures_and_komi(self):
        board = [
            [BLACK, BLACK, BLACK, 0, WHITE],
            [BLACK, 0, BLACK, 0, WHITE],
            [BLACK, BLACK, BLACK, 0, WHITE],
            [0, 0, 0, 0, WHITE],
            [WHITE, WHITE, WHITE, WHITE, WHITE],
        ]
        black, white = calculate_score_japanese(
            board, komi=6.5, black_captures=2, white_captures=3
        )
        self.assertEqual(black, 4.0)  # 黒地1点＋取った白石3個
        self.assertEqual(white, 8.5)  # 白地0点＋取った黒石2個＋コミ


if __name__ == "__main__":
    unittest.main()
