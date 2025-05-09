from tkinter import Tk, Canvas, Label, Menu
#from .random_ai import RandomAI
from .board_utils import BoardUtils
from .mcts import MCTS, GoModel
import numpy as np

class GoGameApp:
    def __init__(self, root, board_size=19, komi=6.5):
        self.root = root
        self.board_size = board_size
        self.cell_size = 40
        self.canvas_size = self.cell_size * board_size
        self.komi = komi

        # アゲハマ表示
        self.black_captures = 0  # 黒のアゲハマ
        self.white_captures = 0  # 白のアゲハマ
        
        # 盤面の状態
        self.board = np.zeros((board_size, board_size), dtype=np.float32)  # 0: 空点, 1: 黒, -1: 白
        self.current_turn = 1  # 1: 黒, -1: 白

        # AIの初期設定
        self.model = GoModel(board_size=board_size)
        self.ai_black = MCTS(self.model, board_size=board_size, simulations=100, c_puct=1.0)
        self.ai_white = MCTS(self.model, board_size=board_size, simulations=100, c_puct=1.0)

        # ゲームモード（デフォルトは人間対AI)
        self.mode = "Human vs AI"
        self.ai_player = -1  # AIが白番を担当 (1: AIが黒番, -1: AIが白番)

        # GUI設定
        self.root.geometry(f"{self.canvas_size + 250}x{self.canvas_size + 250}")
        self.root.title("Hebogo")        

        # メニュー追加
        self.create_menu()

        # 盤面表示
        self.canvas = Canvas(root, width=self.canvas_size, height=self.canvas_size, bg="lightyellow")
        self.canvas.place(x=100, y=100)

        # アゲハマ情報表示
        self.black_label = Label(root, text="Black Captures: 0", font=("Arial", 14), fg="white")
        self.black_label.place(x=20, y=20)  # 左上に表示

        self.white_label = Label(root, text="White Captures: 0", font=("Arial", 14), fg="white")
        self.white_label.place(x=self.canvas_size + 110, y=self.canvas_size + 110)  # 右下に表示

        self.draw_board()
        self.canvas.bind("<Button-1>", self.handle_click)

        # AI対AIモードの場合は、最初のAIの手番を実行
        self.check_ai_turn()

    def create_menu(self):
        """メニューを作成"""
        menu = Menu(self.root)
        self.root.config(menu=menu)

        # ゲームモード選択
        game_menu = Menu(menu, tearoff=0)
        menu.add_cascade(label="ゲームモード", menu=game_menu)
        game_menu.add_command(label="人間 vs 人間", command=lambda: self.set_mode("Human vs Human"))
        game_menu.add_command(label="人間 vs AI", command=lambda: self.set_mode("Human vs AI"))
        game_menu.add_command(label="AI vs AI", command=lambda: self.set_mode("AI vs AI"))

        # AIの担当色設定
        ai_menu = Menu(menu, tearoff=0)
        menu.add_cascade(label="AI設定", menu=ai_menu)
        ai_menu.add_command(label="AIを黒番にする", command=lambda: self.set_ai_color(1))
        ai_menu.add_command(label="AIを白番にする", command=lambda: self.set_ai_color(-1))

    def set_mode(self, mode):
        """ゲームモードを変更"""
        self.mode = mode
        self.reset_game()

    def set_ai_color(self, color):
        """AIの担当色を変更"""
        self.ai_player = color
        self.reset_game()

    def reset_game(self):
        """ゲームをリセット"""
        self.board.fill(0)
        self.black_captures = 0
        self.white_captures = 0
        self.current_turn = 1  # 黒番から開始
        self.update_captures()
        self.draw_board()
        self.check_ai_turn()

    def draw_board(self):
        """碁盤を描画"""
        self.canvas.delete("all")
        for i in range(self.board_size):
            # 縦線
            self.canvas.create_line(
                self.cell_size * (i + 0.5), self.cell_size * 0.5,
                self.cell_size * (i + 0.5), self.cell_size * (self.board_size - 0.5),
                fill="black")
            # 横線
            self.canvas.create_line(
                self.cell_size * 0.5, self.cell_size * (i + 0.5), 
                self.cell_size * (self.board_size - 0.5), self.cell_size * (i + 0.5), 
                fill="black")

        # 石を描画
        for y in range(self.board_size):
            for x in range(self.board_size):
                if self.board[y, x] == 1:
                    self.draw_stone(x, y, "black")
                elif self.board[y, x] == -1:
                    self.draw_stone(x, y, "white")

    def draw_stone(self, x, y, color):
        cx = self.cell_size * (x + 0.5)
        cy = self.cell_size * (y + 0.5)
        radius = self.cell_size * 0.4
        self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill=color)

    def handle_click(self, event):
        """人間の手を処理"""
        if self.mode == "AI vs AI":
            return # AI同士の対戦では人間のクリックを無視

        if self.mode == "Human vs AI" and self.current_turn == self.ai_player:
            return # AIのターンでは人間の手を受け付けない

        # クリック位置を取得
        x = int(event.x // self.cell_size)
        y = int(event.y // self.cell_size)

        # クリック位置に描画
        if 0 <= x < self.board_size and 0 <= y < self.board_size and self.board[y, x] == 0:
            self.board[y, x] = self.current_turn
            captured = BoardUtils.remove_captured_stones(self.board, x, y, -self.current_turn)
            if self.current_turn == 1:
                self.black_captures += captured
            else:
                self.white_captures += captured
            self.update_captures()

            # ターン終了
            self.current_turn *= -1
            self.draw_board()
            self.check_ai_turn()

    def check_ai_turn(self):
        """AIの手番をチェックして実行"""
        if self.mode == "Human vs Human":
            return  # AIの出番なし

        if self.mode == "AI vs AI" or self.current_turn == self.ai_player:
            self.ai_turn()

    def ai_turn(self):
        """ AIの手番を実行 """
        ai = self.ai_black if self.current_turn == 1 else self.ai_white
        action = ai.run(self.board, self.current_turn)
        
        if action is not None:
            x, y = divmod(action, self.board_size)
            self.board[y, x] = self.current_turn
            captured = BoardUtils.remove_captured_stones(self.board, x, y, -self.current_turn)
            if self.current_turn == 1:
                self.black_captures += captured
            else:
                self.white_captures += captured
            self.update_captures()
        
        # ターン終了
        self.current_turn *= -1
        self.draw_board()
        self.check_ai_turn()

    def update_captures(self):
        """アゲハマを更新"""
        self.black_label.config(text=f"Black Captures: {self.black_captures}")
        self.white_label.config(text=f"White Captures: {self.white_captures}")

    def calculate_score(self):
        """地の計算"""
        black_score, white_score = BoardUtils.calculate_score(self.board, self.komi, self.black_captures, self.white_captures)
        return black_score, white_score