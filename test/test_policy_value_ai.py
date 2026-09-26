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
    def test_adds_successful_rescue_outside_policy_top_k_and_records_stones(self):
        board = [
            [BLACK, WHITE, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        scores = [0.0] * 10
        scores[8] = 0.5
        ai = PolicyValueAI(
            FixedPolicy(3, scores), RecordingValue(3, [0.0, 0.0, 0.0]), top_k=1
        )

        self.assertEqual(ai.get_move(board, BLACK), (0, 1))
        rescue = next(item for item in ai.last_analysis.candidates
                      if item.move == (0, 1))
        self.assertEqual(rescue.rescued_stones, 1)
        self.assertEqual(rescue.captured_stones, 0)
        self.assertEqual(rescue.rescue_priority, 1.0)

    def test_does_not_count_extension_that_still_has_one_liberty_as_rescue(self):
        board = [
            [BLACK, WHITE, 0],
            [0, WHITE, 0],
            [0, 0, 0],
        ]
        scores = [0.0] * 10
        scores[8] = 1.0
        ai = PolicyValueAI(
            FixedPolicy(3, scores), RecordingValue(3, [0.0, 0.0]), top_k=1
        )

        ai.get_move(board, BLACK)
        self.assertNotIn((0, 1), [item.move for item in ai.last_analysis.candidates])

    def test_records_capture_candidate_outside_policy_top_k(self):
        board = [
            [WHITE, BLACK, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        scores = [0.0] * 10
        scores[8] = 1.0
        ai = PolicyValueAI(
            FixedPolicy(3, scores), RecordingValue(3, [0.0, 0.0, 0.0]), top_k=1
        )

        ai.get_move(board, BLACK)
        capture = next(item for item in ai.last_analysis.candidates
                       if item.move == (0, 1))
        self.assertEqual(capture.captured_stones, 1)
        self.assertEqual(capture.rescued_stones, 0)

    def test_prefers_rescuing_larger_group(self):
        board = [
            [BLACK, WHITE, 0, WHITE, BLACK],
            [BLACK, WHITE, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        scores = [0.0] * 26
        scores[12] = 0.5
        ai = PolicyValueAI(
            FixedPolicy(5, scores), RecordingValue(5, [0.0] * 4), top_k=1
        )

        self.assertEqual(ai.get_move(board, BLACK), (0, 2))
        rescues = {item.move: item.rescued_stones for item in ai.last_analysis.candidates}
        self.assertEqual(rescues[(0, 2)], 2)
        self.assertEqual(rescues[(4, 1)], 1)

    def test_value_compares_tactical_candidates_with_same_rescue_size(self):
        board = [
            [BLACK, WHITE, 0, WHITE, BLACK],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        scores = [0.0] * 26
        scores[12] = 0.5
        # 候補順はPolicy首位、左の救出、右の救出、PASS。
        value = RecordingValue(5, [0.0, 0.8, -0.8, 0.0])
        ai = PolicyValueAI(FixedPolicy(5, scores), value, top_k=1, value_weight=1.0)

        self.assertEqual(ai.get_move(board, BLACK), (4, 1))

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
        self.assertEqual(ai.last_analysis.selected_move, (1, 0))
        self.assertEqual(ai.last_analysis.policy_weight, 1.0)
        self.assertEqual(len(ai.last_analysis.candidates), 3)
        selected = next(candidate for candidate in ai.last_analysis.candidates
                        if candidate.move == (1, 0))
        self.assertAlmostEqual(selected.value, -0.9)

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
