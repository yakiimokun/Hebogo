class BoardUtils:
    """囲碁盤のユーティリティ機能を提供するクラス"""

    @staticmethod
    def remove_captured_stones(board, x, y, opponent_color):
        """
        相手の石を取り除き、取った石の数を返す
        - 石が囲まれていれば削除し、その数を返す
        """
        size = len(board)
        visited = set()
        captured_stones = []

        def dfs(cx, cy):
            """深さ優先探索でグループを探索"""
            if (cx, cy) in visited:
                return True  # この地点は既に探索済み
            visited.add((cx, cy))

            # 盤外チェック
            if not (0 <= cx < size and 0 <= cy < size):
                return True

            # 呼吸点がある場合は捕獲されていない
            if board[cy][cx] == 0:
                return False

            # 自分の石は無視
            if board[cy][cx] != opponent_color:
                return True

            # 捕獲対象の石として記録
            captured_stones.append((cx, cy))

            # 隣接方向に探索
            fully_surrounded = True
            for nx, ny in [(cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)]:
                if not dfs(nx, ny):
                    fully_surrounded = False

            return fully_surrounded

        # クリックした座標の隣接する相手の石のグループをチェック
        total_captured = 0
        for nx, ny in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]:
            if 0 <= nx < size and 0 <= ny < size and board[ny][nx] == opponent_color:
                visited.clear()
                captured_stones.clear()

                if dfs(nx, ny):
                    # 捕獲対象の石を削除
                    for cx, cy in captured_stones:
                        board[cy][cx] = 0
                    total_captured += len(captured_stones) 

        return total_captured

    @staticmethod
    def get_liberties(board, x, y, color):
        """
        指定した石のグループの呼吸点を数える
        """
        size = len(board)
        visited = set()
        liberties = 0
        stack = [(x, y)]

        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))

            for nx, ny in [(cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)]:
                if 0 <= nx < size and 0 <= ny < size:
                    if board[ny][nx] == '.':
                        liberties += 1
                    elif board[ny][nx] == color:
                        stack.append((nx, ny))

        return liberties

    @staticmethod
    def is_suicide(board, x, y, color):
        """
        自殺手かどうかを判定
        - 仮に置いて呼吸点を確認
        """
        temp_board = [row[:] for row in board]
        temp_board[y][x] = color
        return BoardUtils.get_liberties(temp_board, x, y, color) == 0

    @staticmethod
    def is_ko_violation(board, x, y, color, history):
        """
        劫（コウ）のルール違反を判定
        - 仮に石を置いた盤面が履歴に存在するか確認
        """
        temp_board = [row[:] for row in board]
        temp_board[y][x] = color
        board_string = BoardUtils.board_to_string(temp_board)
        return board_string in history

    @staticmethod
    def board_to_string(board):
        """
        盤面を文字列化（局面を比較可能にするため）
        """
        return "\n".join("".join(row) for row in board)

    @staticmethod
    def calculate_score(board, komi, black_captures, white_captures):
        """
        地を計算
        - 黒と白の得点を返す
        """
        black_score = black_captures
        white_score = white_captures + komi
        size = len(board)

        for y in range(size):
            for x in range(size):
                if board[y][x] == 'B':
                    black_score += 1
                elif board[y][x] == 'W':
                    white_score += 1

        return black_score, white_score
