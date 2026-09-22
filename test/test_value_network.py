"""Value Network の公開入出力を検証する。"""

import unittest

import torch

from src.board_encoder import encode_board
from src.value_network import ValueNetwork


class ValueNetworkTest(unittest.TestCase):
    def test_output_shape_range_and_finiteness(self):
        for size in (9, 13, 19):
            with self.subTest(size=size):
                model = ValueNetwork(board_size=size)
                board = [[0] * size for _ in range(size)]
                board[0][0] = 1
                board[0][1] = -1
                inputs = torch.stack((encode_board(board, 1), encode_board(board, -1)))
                self.assertEqual(inputs.dtype, torch.float32)
                with torch.no_grad():
                    values = model(inputs)
                self.assertEqual(values.shape, (2, 1))
                self.assertTrue(torch.isfinite(values).all().item())
                self.assertTrue(((values >= -1) & (values <= 1)).all().item())

    def test_backward_reaches_trainable_parameters(self):
        model = ValueNetwork(board_size=9)
        value = model(torch.ones(2, 3, 9, 9))
        value.sum().backward()
        parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
        self.assertTrue(parameters)
        self.assertTrue(all(parameter.grad is not None for parameter in parameters))

    def test_invalid_board_size_and_input_shape_are_rejected(self):
        with self.assertRaises(ValueError):
            ValueNetwork(board_size=0)
        model = ValueNetwork(board_size=9)
        for shape in ((3, 9, 9), (1, 2, 9, 9), (1, 3, 13, 13)):
            with self.subTest(shape=shape):
                with self.assertRaises(ValueError):
                    model(torch.zeros(shape))


if __name__ == "__main__":
    unittest.main()
