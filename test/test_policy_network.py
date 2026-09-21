"""Policy Networkの入出力と学習可能性の契約テスト。"""

import unittest

import torch

from src.policy_network import PolicyNetwork


class PolicyNetworkTest(unittest.TestCase):
    def test_output_shape_for_supported_board_sizes(self):
        for size in (9, 13, 19):
            with self.subTest(size=size):
                model = PolicyNetwork(board_size=size)
                with torch.no_grad():
                    logits = model(torch.zeros(2, 3, size, size))
                self.assertEqual(logits.shape, (2, size * size + 1))
                self.assertTrue(torch.isfinite(logits).all().item())

    def test_head_returns_logits_without_softmax(self):
        model = PolicyNetwork(board_size=2)
        with torch.no_grad():
            model.policy_head.weight.zero_()
            model.policy_head.bias.fill_(2.0)
            logits = model(torch.zeros(1, 3, 2, 2))
        self.assertTrue(torch.all(logits == 2.0).item())
        self.assertEqual(logits.shape[-1], 5)  # 4交点 + パス

    def test_backward_reaches_convolution_and_head(self):
        model = PolicyNetwork(board_size=3)
        logits = model(torch.ones(1, 3, 3, 3))
        logits.sum().backward()
        self.assertIsNotNone(model.conv[0].weight.grad)
        self.assertIsNotNone(model.policy_head.weight.grad)

    def test_invalid_board_size_and_input_shape_are_rejected(self):
        with self.assertRaises(ValueError):
            PolicyNetwork(board_size=0)
        model = PolicyNetwork(board_size=9)
        for shape in ((3, 9, 9), (1, 2, 9, 9), (1, 3, 13, 13)):
            with self.subTest(shape=shape):
                with self.assertRaises(ValueError):
                    model(torch.zeros(shape))


if __name__ == "__main__":
    unittest.main()
