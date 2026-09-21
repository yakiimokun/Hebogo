import unittest

import torch

from src.policy_ai import PolicyAI
from src.rules import BLACK, WHITE


class FixedModel(torch.nn.Module):
    def __init__(self, board_size, scores):
        super().__init__()
        self.board_size = board_size
        self.register_buffer("scores", torch.tensor(scores, dtype=torch.float32))

    def forward(self, inputs):
        return self.scores.unsqueeze(0).expand(inputs.shape[0], -1)


class PolicyAITest(unittest.TestCase):
    def test_selects_highest_legal_point_and_uses_xy_coordinates(self):
        scores = [0.0] * 10
        scores[7] = 8.0  # x=1, y=2
        ai = PolicyAI(FixedModel(3, scores))
        self.assertEqual(ai.get_move([[0] * 3 for _ in range(3)], BLACK), (1, 2))

    def test_masks_occupied_point(self):
        scores = [0.0] * 10
        scores[0] = 100.0
        scores[1] = 5.0
        ai = PolicyAI(FixedModel(3, scores))
        self.assertEqual(ai.get_move([[BLACK, 0, 0], [0] * 3, [0] * 3], WHITE), (1, 0))

    def test_masks_suicide_and_ko_repetition(self):
        scores = [0.0] * 26
        scores[12] = 100.0  # 囲まれた中央は自殺手
        scores[0] = 5.0
        board = [[0] * 5 for _ in range(5)]
        for x, y in ((2, 1), (1, 2), (3, 2), (2, 3)):
            board[y][x] = WHITE
        ai = PolicyAI(FixedModel(5, scores))
        self.assertEqual(ai.get_move(board, BLACK), (0, 0))
        previous = [row[:] for row in board]
        previous[0][0] = BLACK
        self.assertNotEqual(ai.get_move(board, BLACK, previous_board=previous), (0, 0))

    def test_selects_pass_and_passes_when_no_legal_point(self):
        scores = [0.0] * 10
        scores[-1] = 10.0
        ai = PolicyAI(FixedModel(3, scores))
        self.assertIsNone(ai.get_move([[0] * 3 for _ in range(3)], BLACK))
        self.assertIsNone(ai.get_move([[WHITE] * 3 for _ in range(3)], BLACK))

    def test_rejects_invalid_board_or_logits(self):
        ai = PolicyAI(FixedModel(3, [0.0] * 10))
        with self.assertRaises(ValueError):
            ai.get_move([[0] * 2 for _ in range(2)], BLACK)
        with self.assertRaises(ValueError):
            PolicyAI(FixedModel(3, [0.0] * 9)).get_move([[0] * 3 for _ in range(3)], BLACK)
        scores = [0.0] * 10
        scores[0] = float("nan")
        with self.assertRaises(ValueError):
            PolicyAI(FixedModel(3, scores)).get_move([[0] * 3 for _ in range(3)], BLACK)


if __name__ == "__main__":
    unittest.main()
