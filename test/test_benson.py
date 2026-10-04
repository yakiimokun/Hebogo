"""Bensonの生きの保証、領域の依存関係、評価への安全な利用を検証する。"""

import unittest

from src.benson import analyze_benson, BensonMoveAssessment
from src.rules import BLACK, WHITE, play_move


def position(*rows):
    values = {"X": BLACK, "O": WHITE, ".": 0}
    return [[values[cell] for cell in row] for row in rows]


class BensonTest(unittest.TestCase):
    def test_two_eyes_both_colors_and_no_mutation(self):
        for color in (BLACK, WHITE):
            for size in (5, 9, 13, 19):
                with self.subTest(color=color, size=size):
                    board = [[color] * size for _ in range(size)]
                    board[1][1] = board[1][3] = 0
                    original = [row[:] for row in board]
                    result = analyze_benson(board, color)
                    self.assertEqual(len(result.alive_stones), size * size - 2)
                    self.assertEqual(len(result.alive_chains), 1)
                    self.assertEqual(result.empty_eye_points, {(1, 1), (3, 1)})
                    self.assertEqual(board, original)

    def test_single_eye_and_large_undivided_space_are_not_two_eyes(self):
        for board in (
            position("XXXXX", "X.XXX", "XXXXX", "XXXXX", "XXXXX"),
            position("XXXXX", "X...X", "X...X", "X...X", "XXXXX"),
            [[0] * 5 for _ in range(5)],
        ):
            self.assertFalse(analyze_benson(board, BLACK).alive_stones)

    def test_unsafe_boundary_causes_cascading_removal(self):
        # 中央の1子は上下の2領域に接するが、境界の上下の連は一眼だけ。
        board = position(
            ".......", ".XXX...", ".X.X...", "..X....",
            ".X.X...", ".XXX...", ".......",
        )
        result = analyze_benson(board, BLACK)
        self.assertFalse(result.alive_stones)
        self.assertFalse(result.vital_regions)
        self.assertFalse(result.empty_eye_points)

    def test_opponent_stones_belong_to_region_but_not_empty_eye_penalty(self):
        board = position("XXXXX", "X..XX", "XO.XX", "XXX.X", "XXXXX")
        result = analyze_benson(board, BLACK)
        self.assertEqual(len(result.alive_stones), 20)
        self.assertEqual(len(result.vital_regions), 2)
        self.assertEqual(result.empty_eye_points, {(3, 3)})
        self.assertTrue(any((1, 2) in region for region in result.vital_regions))
        self.assertFalse(analyze_benson(board, WHITE).alive_stones)

    def test_board_edge_can_bound_eyes(self):
        board = position(".X.XX", "XXXXX", "XXXXX", "XXXXX", "XXXXX")
        self.assertEqual(len(analyze_benson(board, BLACK).alive_stones), 23)

    def test_multiple_chains_can_support_each_other(self):
        board = position("XXX..", "X.X..", ".X...", "X.X..", "XXX..")
        result = analyze_benson(board, BLACK)
        self.assertEqual(len(result.alive_chains), 3)
        self.assertEqual(len(result.alive_stones), 11)

    def test_seki_and_ko_are_not_reported_as_pass_alive(self):
        seki = position("XXO", "X.O", ".OO")
        ko = position(".....", "..XO.", ".XO.O", "..XO.", ".....")
        for board in (seki, ko):
            for color in (BLACK, WHITE):
                with self.subTest(board=board, color=color):
                    self.assertFalse(analyze_benson(board, color).alive_stones)

    def test_filling_eye_loses_certificate_but_pass_does_not(self):
        board = position("XXXXX", "X.X.X", "XXXXX", "XXXXX", "XXXXX")
        own = analyze_benson(board, BLACK)
        opponent = analyze_benson(board, WHITE)
        played = play_move(board, 1, 1, BLACK)
        self.assertTrue(played.legal)
        assessment = BensonMoveAssessment.evaluate(played.board, (1, 1), own, opponent)
        self.assertTrue(assessment.fills_own_eye)
        self.assertEqual(assessment.lost_alive_stones, 23)
        self.assertEqual(assessment.penalty, 23.0)
        passed = BensonMoveAssessment.evaluate(board, None, own, opponent)
        self.assertEqual(passed.penalty, 0.0)

    def test_empty_two_point_eye_invasion_is_penalized(self):
        board = position("OOOOO", "O..OO", "OOOOO", "OOO.O", "OOOOO")
        own = analyze_benson(board, BLACK)
        opponent = analyze_benson(board, WHITE)
        played = play_move(board, 1, 1, BLACK)
        self.assertTrue(played.legal)
        assessment = BensonMoveAssessment.evaluate(played.board, (1, 1), own, opponent)
        self.assertTrue(assessment.invades_alive_eye)
        self.assertEqual(assessment.penalty, 1.0)

    def test_rejects_invalid_inputs(self):
        for board, color in (([], BLACK), ([[0, 0]], BLACK), ([[2]], BLACK), ([[0]], 0)):
            with self.subTest(board=board, color=color), self.assertRaises(ValueError):
                analyze_benson(board, color)


if __name__ == "__main__":
    unittest.main()
