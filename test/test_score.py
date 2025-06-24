import unittest
import numpy as np
import sys
import os

# srcディレクトリをPythonパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.board_utils import BoardUtils

class TestScoreCalculation(unittest.TestCase):
    def setUp(self):
        """テストの前準備"""
        self.board_size = 9
        self.komi = 6.5

    def test_empty_board(self):
        """空の盤面での地の計算"""
        self.board = np.zeros((self.board_size, self.board_size), dtype=np.int8)
        black_score, white_score = BoardUtils.calculate_score_japanese(self.board, self.komi, 0, 0)
        self.assertEqual(black_score, 0)
        self.assertEqual(white_score, self.komi)

    def test_simple_territory(self):
        """単純な地の計算"""
        self.board = np.zeros((self.board_size, self.board_size), dtype=np.int8)
        # 黒が左上の角を囲む
        self.board[0:3, 0:3] = 1
        self.board[1:2, 1:2] = 0  # 中心を空ける
        black_score, white_score = BoardUtils.calculate_score_japanese(self.board, self.komi, 0, 0)
        self.assertEqual(black_score, 1)  # 中心の1点の地
        self.assertEqual(white_score, self.komi)

    def test_captured_stones(self):
        """アゲハマを含む地の計算"""
        self.board = np.zeros((self.board_size, self.board_size), dtype=np.int8)
        # 黒が白石を1つ取る
        self.board[0:3, 0:3] = 1
        self.board[1, 1] = -1
        black_captures = 1  # 黒のアゲハマを設定
        white_captures = 0  # 白のアゲハマを設定
        black_score, white_score = BoardUtils.calculate_score_japanese(self.board, self.komi, black_captures, white_captures)
        self.assertEqual(black_score, 2)  # アゲハマ1個
        self.assertEqual(white_score, self.komi)

    def test_complex_territory(self):
        """複雑な地の計算"""
        self.board = np.zeros((self.board_size, self.board_size), dtype=np.int8)
        # 黒が左側を囲む
        self.board[:, 0:3] = 1
        # 白が右側を囲む
        self.board[:, 6:9] = -1
        # 中央に空点
        self.board[3:6, 3:6] = 0
        black_captures = 0
        white_captures = 0
        black_score, white_score = BoardUtils.calculate_score_japanese(self.board, self.komi, black_captures, white_captures)
        self.assertEqual(black_score, 9)  # 中央の空点が黒地
        self.assertEqual(white_score, self.komi)

    def test_neutral_territory(self):
        """中立地の計算"""
        self.board = np.zeros((self.board_size, self.board_size), dtype=np.int8)
        # 黒と白が交互に並ぶ
        for i in range(self.board_size):
            if i % 2 == 0:
                self.board[i, :] = 1
            else:
                self.board[i, :] = -1
        black_captures = 0
        white_captures = 0
        black_score, white_score = BoardUtils.calculate_score_japanese(self.board, self.komi, black_captures, white_captures)
        self.assertEqual(black_score, 0)  # 中立地はカウントされない
        self.assertEqual(white_score, self.komi)

    def test_edge_case(self):
        """端のケースのテスト"""
        self.board = np.zeros((self.board_size, self.board_size), dtype=np.int8)
        # 黒が端を囲む
        self.board[0, :] = 1
        self.board[-1, :] = 1
        self.board[:, 0] = 1
        self.board[:, -1] = 1
        black_captures = 0
        white_captures = 0
        black_score, white_score = BoardUtils.calculate_score_japanese(self.board, self.komi, black_captures, white_captures)
        self.assertEqual(black_score, 49)  # 内側の地
        self.assertEqual(white_score, self.komi)

if __name__ == '__main__':
    unittest.main()