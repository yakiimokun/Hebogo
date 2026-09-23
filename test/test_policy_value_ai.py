import unittest

import torch

from src.policy_ai import PolicyAI
from src.policy_value_ai import PolicyValueAI
from src.rules import BLACK, WHITE


class FixedPolicy(torch.nn.Module):
    def __init__(self, size, scores):
        super().__init__()
        self.board_size = size
        self.register_buffer("scores", torch.tensor(scores, dtype=torch.float32))

    def forward(self, inputs):
        return self.scores.unsqueeze(0).expand(inputs.shape[0], -1)


class RecordingValue(torch.nn.Module):
    def __init__(self, size, values):
        super().__init__()
        self.board_size = size
        self.values = values
        self.last_inputs = None

    def forward(self, inputs):
        self.last_inputs = inputs.clone()
        return torch.tensor(self.values, dtype=torch.float32).reshape(-1, 1)


class PolicyValueAITest(unittest.TestCase):
    def test_reranks_top_candidates_using_next_players_view(self):
        scores = [0.0] * 10
        scores[0], scores[1], scores[2] = 3.0, 2.0, 1.0
        value = RecordingValue(3, [0.8, -0.9, -0.2])
        ai = PolicyValueAI(FixedPolicy(3, scores), value, top_k=2, value_weight=1.0)
        self.assertEqual(ai.get_move([[0] * 3 for _ in range(3)], BLACK), (1, 0))
        self.assertEqual(tuple(value.last_inputs.shape), (3, 3, 3, 3))
        # 候補着手後の盤面を、白の手番から見たチャンネルで符号化する。
        self.assertEqual(value.last_inputs[0, 2, 0, 0].item(), 1)
        self.assertEqual(value.last_inputs[1, 2, 0, 1].item(), 1)
        self.assertEqual(value.last_inputs[2, 0].sum().item(), 9)  # パス

    def test_pass_is_evaluated_even_outside_top_k(self):
        scores = [0.0] * 10
        scores[0] = 3.0
        scores[-1] = -3.0
        ai = PolicyValueAI(FixedPolicy(3, scores), RecordingValue(3, [1.0, -1.0]),
                           top_k=1, value_weight=1.0)
        self.assertIsNone(ai.get_move([[0] * 3 for _ in range(3)], BLACK))

    def test_softmax_uses_all_legal_moves_including_pass(self):
        # 最高の合法手も、他の合法手が多数あれば確率は小さい。
        scores = [0.0] * 10
        scores[0] = 0.2
        scores[-1] = -1.0
        ai = PolicyValueAI(FixedPolicy(3, scores), RecordingValue(3, [-0.1, -0.2]),
                           top_k=1, value_weight=1.0)
        self.assertIsNone(ai.get_move([[0] * 3 for _ in range(3)], BLACK))

    def test_occupied_and_history_forbidden_points_are_excluded(self):
        scores = [0.0] * 10
        scores[0], scores[1], scores[2] = 10.0, 9.0, 8.0
        board = [[BLACK, 0, 0], [0] * 3, [0] * 3]
        repeated = [[BLACK, BLACK, 0], [0] * 3, [0] * 3]
        value = RecordingValue(3, [0.0, 0.0])
        ai = PolicyValueAI(FixedPolicy(3, scores), value, top_k=1)
        self.assertEqual(ai.get_move(board, BLACK, history=iter([repeated])), (2, 0))
        self.assertEqual(value.last_inputs[0, 2, 0, 2].item(), 1)

    def test_value_absent_matches_policy_ai(self):
        scores = [0.0] * 10
        scores[4] = 5.0
        policy = FixedPolicy(3, scores)
        board = [[0] * 3 for _ in range(3)]
        self.assertEqual(PolicyValueAI(policy).get_move(board, WHITE),
                         PolicyAI(policy).get_move(board, WHITE))

    def test_rejects_size_shape_and_non_finite_values(self):
        policy = FixedPolicy(3, [0.0] * 10)
        board = [[0] * 3 for _ in range(3)]
        with self.assertRaises(ValueError):
            PolicyValueAI(policy, RecordingValue(2, [0.0]))
        with self.assertRaises(ValueError):
            PolicyValueAI(policy, RecordingValue(3, [0.0] * 5)).get_move(board, BLACK)
        for bad in (float("nan"), float("inf"), 1.1):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                PolicyValueAI(policy, RecordingValue(3, [bad] * 6)).get_move(board, BLACK)


if __name__ == "__main__":
    unittest.main()
