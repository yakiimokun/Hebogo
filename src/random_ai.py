from .board_utils import BoardUtils
import random

class RandomAI:
    """ランダムに合法手を選ぶAI"""
    def __init__(self, color):
        self.color = color
        self.history = []  # 局面履歴

    def get_move(self, board):
        """合法手からランダムに選ぶ"""
        legal_moves = self.get_legal_moves(board, self.color)
        return random.choice(legal_moves) if legal_moves else (None, None)

    def get_legal_moves(self, board, color):
        """
        合法手を計算
        - 自殺手、劫を除外
        """
        size = len(board)
        legal_moves = []
        opponent_color = 'B' if color == 'W' else 'W'

        for y in range(size):
            for x in range(size):
                if board[y][x] == '.':
                    if not BoardUtils.is_suicide(board, x, y, color) and not BoardUtils.is_ko_violation(board, x, y, color, self.history):
                        legal_moves.append((x, y))
        return legal_moves

    def update_history(self, board):
        """現在の盤面を履歴に追加"""
        self.history.append(BoardUtils.board_to_string(board))