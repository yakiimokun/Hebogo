"""Policy Networkへ渡す盤面表現の契約テスト。"""

import unittest

import torch

from src.board_encoder import encode_board, index_to_point, point_to_index
from src.rules import BLACK, EMPTY, WHITE


class BoardEncoderTest(unittest.TestCase):
    def test_channels_for_black_turn(self):
        board = [
            [BLACK, EMPTY, WHITE],
            [EMPTY, WHITE, BLACK],
            [EMPTY, EMPTY, EMPTY],
        ]

        encoded = encode_board(board, BLACK)

        self.assertEqual(encoded.shape, (3, 3, 3))
        self.assertEqual(encoded.dtype, torch.float32)
        self.assertEqual(encoded[:, 0, 0].tolist(), [0.0, 1.0, 0.0])
        self.assertEqual(encoded[:, 0, 1].tolist(), [1.0, 0.0, 0.0])
        self.assertEqual(encoded[:, 0, 2].tolist(), [0.0, 0.0, 1.0])
        self.assertTrue(torch.all(encoded.sum(dim=0) == 1))

    def test_white_turn_swaps_current_and_opponent(self):
        board = [[BLACK, WHITE], [EMPTY, EMPTY]]

        encoded = encode_board(board, WHITE)

        self.assertEqual(encoded[:, 0, 0].tolist(), [0.0, 0.0, 1.0])
        self.assertEqual(encoded[:, 0, 1].tolist(), [0.0, 1.0, 0.0])
        self.assertEqual(encoded[:, 1, 0].tolist(), [1.0, 0.0, 0.0])

    def test_bad_board_or_color_is_rejected(self):
        for board, color in (
            ([], BLACK),
            ([[EMPTY, EMPTY]], BLACK),
            ([[EMPTY], [EMPTY]], BLACK),
            ([[2]], BLACK),
            ([[EMPTY]], EMPTY),
        ):
            with self.subTest(board=board, color=color):
                with self.assertRaises(ValueError):
                    encode_board(board, color)

    def test_move_index_is_row_major_and_pass_is_last(self):
        self.assertEqual(point_to_index((0, 0), 9), 0)
        self.assertEqual(point_to_index((2, 1), 9), 11)
        self.assertEqual(point_to_index((8, 8), 9), 80)
        self.assertEqual(point_to_index(None, 9), 81)
        self.assertEqual(index_to_point(11, 9), (2, 1))
        self.assertIsNone(index_to_point(81, 9))

    def test_indices_round_trip(self):
        for size in (9, 13, 19):
            for index in range(size * size + 1):
                with self.subTest(size=size, index=index):
                    self.assertEqual(
                        point_to_index(index_to_point(index, size), size),
                        index,
                    )

    def test_invalid_indices_and_points_are_rejected(self):
        for point in ((-1, 0), (9, 0), (0, 9), (0.5, 1)):
            with self.subTest(point=point):
                with self.assertRaises(ValueError):
                    point_to_index(point, 9)
        for index in (-1, 82, 1.5):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    index_to_point(index, 9)
        with self.assertRaises(ValueError):
            point_to_index((0, 0), 0)


if __name__ == "__main__":
    unittest.main()
