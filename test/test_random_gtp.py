import random
import unittest

from src.gtp_match import GTPMatch
from src.random_ai import RandomAI
from src.random_gtp_engine import RandomGTPEngine, point_to_vertex, vertex_to_point
from src.rules import BLACK, WHITE


class RandomAITest(unittest.TestCase):
    def test_selects_only_legal_empty_point(self):
        board = [[0, -1, 0], [-1, 0, -1], [0, -1, 0]]
        ai = RandomAI(BLACK, random.Random(1))
        self.assertNotIn((1, 1), ai.get_legal_moves(board))
        self.assertNotEqual(ai.get_move(board), (1, 1))

    def test_returns_none_when_no_legal_move(self):
        self.assertIsNone(RandomAI(BLACK).get_move([[-1, -1], [-1, -1]]))

    def test_does_not_fill_own_eye(self):
        board = [
            [0, BLACK, 0, 0, 0],
            [BLACK, BLACK, BLACK, 0, 0],
            [0, BLACK, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        self.assertNotIn((0, 0), RandomAI(BLACK).get_worthwhile_moves(board))

    def test_passes_when_only_own_eyes_are_legal(self):
        board = [
            [0, BLACK, BLACK],
            [BLACK, BLACK, BLACK],
            [BLACK, BLACK, 0],
        ]
        self.assertIsNone(RandomAI(BLACK).get_move(board))

    def test_does_not_play_non_capturing_self_atari(self):
        board = [
            [0, WHITE, 0],
            [WHITE, 0, 0],
            [0, WHITE, 0],
        ]
        self.assertNotIn((1, 1), RandomAI(BLACK).get_worthwhile_moves(board))

    def test_keeps_capture_even_when_it_fills_an_eye_shape(self):
        board = [
            [BLACK, BLACK, BLACK],
            [BLACK, WHITE, 0],
            [BLACK, BLACK, BLACK],
        ]
        self.assertEqual(RandomAI(BLACK).get_move(board), (2, 1))


class RandomGTPEngineTest(unittest.TestCase):
    def test_vertex_conversion_skips_i(self):
        self.assertEqual(point_to_vertex((8, 0), 19), "J19")
        self.assertEqual(vertex_to_point("J19", 19), (8, 0))

    def test_genmove_updates_board(self):
        engine = RandomGTPEngine(board_size=3, seed=3)
        point = vertex_to_point(engine.send_command("genmove black"), 3)
        self.assertEqual(engine.board[point[1]][point[0]], BLACK)

    def test_genmove_passes_without_changing_board_when_only_eyes_remain(self):
        engine = RandomGTPEngine(board_size=3, seed=3)
        engine.board = [
            [0, BLACK, BLACK],
            [BLACK, BLACK, BLACK],
            [BLACK, BLACK, 0],
        ]
        engine.history = [[row[:] for row in engine.board]]
        before = [row[:] for row in engine.board]

        self.assertEqual(engine.send_command("genmove black"), "pass")
        self.assertEqual(engine.board, before)
        self.assertEqual(len(engine.history), 2)

    def test_two_engines_play_through_gtp(self):
        black = RandomGTPEngine(seed=1)
        white = RandomGTPEngine(seed=2)
        result = GTPMatch(black, white, board_size=3).play(max_moves=40)
        self.assertIn(result.reason, ("two_passes", "move_limit"))
        self.assertEqual(black.board, white.board)
        self.assertGreater(len(result.moves), 0)


if __name__ == "__main__":
    unittest.main()
