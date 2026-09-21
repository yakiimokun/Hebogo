import io
import tempfile
import unittest

import torch

from src.gtp_match import GTPMatch
from src.policy_gtp_engine import PolicyGTPEngine
from src.policy_network import PolicyNetwork
from src.random_gtp_engine import RandomGTPEngine
from src.rules import BLACK, WHITE


class FixedModel(torch.nn.Module):
    def __init__(self, board_size, index):
        super().__init__()
        self.board_size = board_size
        self.index = index

    def forward(self, inputs):
        scores = torch.zeros(inputs.shape[0], self.board_size ** 2 + 1)
        scores[:, self.index] = 10.0
        return scores


class PolicyGTPEngineTest(unittest.TestCase):
    def test_requires_trained_model_and_matching_board_size(self):
        with self.assertRaises(ValueError):
            PolicyGTPEngine(board_size=3)
        with self.assertRaises(ValueError):
            PolicyGTPEngine(board_size=9, model=FixedModel(3, 0))

    def test_loads_state_dict_checkpoint(self):
        with tempfile.NamedTemporaryFile(suffix=".pt") as checkpoint:
            torch.save(PolicyNetwork(board_size=3).state_dict(), checkpoint.name)
            engine = PolicyGTPEngine(board_size=3, model_path=checkpoint.name)
            self.assertEqual(engine.board_size, 3)
        with self.assertRaises(ValueError):
            PolicyGTPEngine(board_size=3, model_path="/nonexistent/policy.pt")

    def test_genmove_and_play_update_board(self):
        engine = PolicyGTPEngine(board_size=3, model=FixedModel(3, 0))
        self.assertEqual(engine.genmove("black"), "A3")
        self.assertEqual(engine.board[0][0], BLACK)
        self.assertTrue(engine.play("white", "B3"))
        self.assertEqual(engine.board[0][1], WHITE)
        self.assertFalse(engine.play("black", "B3"))
        self.assertEqual(engine.board[0][1], WHITE)
        board, black_captures, white_captures = engine.showboard()
        self.assertEqual((black_captures, white_captures), (0, 0))
        board[0][0] = 0
        self.assertEqual(engine.board[0][0], BLACK)

    def test_pass_and_invalid_commands(self):
        engine = PolicyGTPEngine(board_size=3, model=FixedModel(3, 9))
        self.assertEqual(engine.genmove("b"), "pass")
        self.assertEqual(len(engine.history), 2)
        self.assertTrue(engine.play("white", "pass"))
        self.assertEqual(len(engine.history), 3)
        self.assertFalse(engine.set_board_size(9))
        self.assertEqual(engine.board_size, 3)
        self.assertIsNone(engine.send_command("play black Z9"))
        self.assertIsNone(engine.send_command("genmove purple"))
        self.assertTrue(engine.komi(7.5))
        self.assertEqual(engine.get_final_score(), "W+7.5")
        engine.close()

    def test_gtp_stdio_success_error_and_quit(self):
        engine = PolicyGTPEngine(board_size=3, model=FixedModel(3, 9))
        output = io.StringIO()
        engine.run(io.StringIO("name\nunknown\nquit\nname\n"), output)
        self.assertEqual(output.getvalue(), "= Hebogo Policy AI\n\n? command failed\n\n= \n\n")

    def test_matches_random_engine_through_gtp(self):
        policy = PolicyGTPEngine(board_size=3, model=FixedModel(3, 0))
        random = RandomGTPEngine(board_size=3, seed=4)
        result = GTPMatch(policy, random, board_size=3).play(max_moves=30)
        self.assertIn(result.reason, ("two_passes", "move_limit"))
        self.assertEqual(policy.board, random.board)
        self.assertGreater(len(result.moves), 0)


if __name__ == "__main__":
    unittest.main()
