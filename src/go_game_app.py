from tkinter import Tk, Canvas, Label, Menu, Button, ttk, messagebox
import tkinter as tk
from PIL import Image, ImageTk
import subprocess
import time
import os
from .gtp_client import GTPClient
from .rules import KO, OCCUPIED, OUT_OF_BOUNDS, SUICIDE, calculate_score_japanese, play_move

class GoGameApp:
    def __init__(self, root, board_size=19, komi=6.5, black_type="player", white_type="Random AI", gtp_client=None, ai_engines=None):
        self.root = root
        self.board_size = board_size
        self.cell_size = 40
        self.canvas_size = self.cell_size * board_size
        self.board_left = 220
        self.board_top = 50
        self.komi = komi

        self.black_type = "Player" if black_type == "player" else black_type
        self.white_type = "Player" if white_type == "player" else white_type
        self.gtp_client = gtp_client
        self.ai_engines = ai_engines or {}

        # 石の画像を読み込む（アゲハマ表示用）
        self.load_stone_images()

        # アゲハマ表示
        self.black_captures = 0  # 黒のアゲハマ
        self.white_captures = 0  # 白のアゲハマ
        
        # 盤面の状態
        self.board = [[0 for _ in range(board_size)] for _ in range(board_size)]  # 0: 空点, 1: 黒, -1: 白
        self.board_history = [[row[:] for row in self.board]]
        self.current_turn = 1  # 1: 黒, -1: 白

        # GUI設定
        self.root.geometry(f"{self.board_left + self.canvas_size + 200}x{self.canvas_size + 180}")
        self.root.title("Hebogo")        

        # メニュー追加
        self.create_menu()

        # 盤面表示
        self.canvas = Canvas(root, width=self.canvas_size, height=self.canvas_size, bg="lightyellow")
        self.canvas.place(x=self.board_left, y=self.board_top)

        # 白の情報表示（左上）
        self.white_frame = tk.Frame(root)
        self.white_frame.place(x=20, y=100)  # 碁盤と同じ高さに配置
        
        # 白のプレーヤー名
        self.white_label = Label(self.white_frame, text="", font=("Arial", 14), fg="black")
        self.white_label.pack(pady=(0, 5))  # 下の余白を調整
        
        # 白の手番表示用のキャンバス
        self.turn_indicator = Canvas(self.white_frame, width=20, height=20, bg=None, highlightthickness=0)
        self.turn_indicator.pack(pady=(0, 10))

        # 白のアゲハマ表示用のキャンバス（透明対応）
        self.white_captures_canvas = Canvas(self.white_frame, width=self.cell_size * 3, height=self.cell_size, bg=None, highlightthickness=0)
        self.white_captures_canvas.pack(pady=(0, 10))  # 下の余白を調整
                
        # 白のボタン
        self.white_pass_button = Button(self.white_frame, text="Pass", command=lambda: self.handle_pass(-1), width=10)
        self.white_pass_button.pack(pady=2)
        
        self.white_resign_button = Button(self.white_frame, text="Resign", command=lambda: self.handle_resign(-1), width=10)
        self.white_resign_button.pack(pady=2)

        # 黒の情報表示（右下）
        self.black_frame = tk.Frame(root)
        self.black_frame.place(x=self.board_left + self.canvas_size + 40, y=self.canvas_size - 160)
        
        # 黒のプレーヤー名
        self.black_label = Label(self.black_frame, text="", font=("Arial", 14), fg="black")
        self.black_label.pack(pady=(0, 5))  # 下の余白を調整
        
        # 黒の手番表示用のキャンバス
        self.turn_indicator2 = Canvas(self.black_frame, width=20, height=20, bg=None, highlightthickness=0)
        self.turn_indicator2.pack(pady=(0, 10))
        
        # 白の手番表示用のキャンバス
        self.turn_indicator = Canvas(self.white_frame, width=20, height=20, bg=None, highlightthickness=0)
        self.turn_indicator.pack(pady=(0, 10))

        # 黒のアゲハマ表示用のキャンバス（透明対応）
        self.black_captures_canvas = Canvas(self.black_frame, width=self.cell_size * 3, height=self.cell_size, bg=None, highlightthickness=0)
        self.black_captures_canvas.pack(pady=(0, 10))  # 下の余白を調整
        
        # 黒のボタン
        self.black_pass_button = Button(self.black_frame, text="Pass", command=lambda: self.handle_pass(1), width=10)
        self.black_pass_button.pack(pady=2)
        
        self.black_resign_button = Button(self.black_frame, text="Resign", command=lambda: self.handle_resign(1), width=10)
        self.black_resign_button.pack(pady=2)

        # パスと投了の状態を追跡
        self.last_move_was_pass = False
        self.game_over = False

        self.draw_board()
        self.canvas.bind("<Button-1>", self.handle_click)

        # 初期状態の更新
        self.update_captures()  # プレーヤー情報を表示
        self.update_button_states()  # ボタンの状態を更新

        # AIの手番をチェック
        self.check_ai_turn()

    def load_stone_images(self):
        """石の画像を読み込む（アゲハマ表示用）"""
        # 画像の読み込みとリサイズ（RGBAで透明対応）
        white_img = Image.open("./whitestone.png").convert("RGBA")
        black_img = Image.open("./blackstone.png").convert("RGBA")
        
        # 石のサイズを碁盤のマス目に合わせる（アスペクト比を保持）
        stone_size = int(self.cell_size)
        white_img = white_img.resize((stone_size, stone_size), Image.Resampling.LANCZOS)
        black_img = black_img.resize((stone_size, stone_size), Image.Resampling.LANCZOS)
        
        # PhotoImageに変換
        self.white_stone_img = ImageTk.PhotoImage(white_img)
        self.black_stone_img = ImageTk.PhotoImage(black_img)

    def draw_single_stone(self, x, y, color):
        """単一の石を描画（既存の石を消去せずに）"""
        cx = self.cell_size * (x + 0.5)
        cy = self.cell_size * (y + 0.5)
        radius = self.cell_size * 0.4
        # 単純な円形で描画
        self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, 
                              fill=color, outline="black", width=1)

    def create_menu(self):
        """メニューを作成"""
        menu = Menu(self.root)
        self.root.config(menu=menu)

        # ゲームモード選択
        game_menu = Menu(menu, tearoff=0)
        menu.add_cascade(label="Game Mode", menu=game_menu)
        game_menu.add_command(label="Human vs Human", command=lambda: self.set_mode("Human vs Human"))
        game_menu.add_command(label="Human vs AI", command=lambda: self.set_mode("Human vs AI"))
        game_menu.add_command(label="AI vs AI", command=lambda: self.set_mode("AI vs AI"))

    def set_mode(self, mode):
        """ゲームモードを変更"""
        if mode == "Human vs Human":
            self.black_type = "Player"
            self.white_type = "Player"
        elif mode == "Human vs AI":
            self.black_type = "Player"
            self.white_type = "AI"
        elif mode == "AI vs AI":
            self.black_type = "AI"
            self.white_type = "AI"
        
        self.reset_game()
        self.update_captures()  # プレーヤー情報を更新

    def reset_game(self):
        """ゲームをリセット"""
        for y in range(self.board_size):
            for x in range(self.board_size):
                self.board[y][x] = 0
        self.black_captures = 0
        self.white_captures = 0
        self.current_turn = 1
        self.board_history = [[row[:] for row in self.board]]
        self.last_move_was_pass = False
        self.game_over = False
        self.update_captures()
        self.draw_board()
        self.update_button_states()
        
        # 使用中のGTPエンジンを同じ初期状態にする。
        if not self.is_human_match():
            for engine in self.unique_engines():
                engine.clear_board()
                engine.set_board_size(self.board_size)
                engine.komi(self.komi)
        
        self.check_ai_turn()

    def is_human_match(self):
        """両対局者が人間かを返す。"""
        return self.black_type == "Player" and self.white_type == "Player"

    def is_ai_turn(self):
        """現在の手番にAIエンジンが割り当てられているかを返す。"""
        return self.current_turn in self.ai_engines

    def unique_engines(self):
        """同一インスタンスを重複させず、使用中のエンジンを返す。"""
        return list(dict.fromkeys(self.ai_engines.values()))

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

        if self.board_size == 19:
            # 4・10・16路の交点（中央が天元）に星を描く。
            for y in (3, 9, 15):
                for x in (3, 9, 15):
                    cx = self.cell_size * (x + 0.5)
                    cy = self.cell_size * (y + 0.5)
                    radius = 4
                    self.canvas.create_oval(
                        cx - radius, cy - radius, cx + radius, cy + radius,
                        fill="black", outline="black",
                    )

        # 石を描画
        for y in range(self.board_size):
            for x in range(self.board_size):
                if self.board[y][x] == 1:
                    self.draw_single_stone(x, y, "black")
                elif self.board[y][x] == -1:
                    self.draw_single_stone(x, y, "white")

    def update_board_from_gtp(self, engine=None):
        """全エンジンの盤面一致を確認し、GTPの盤面を描画する。"""
        engines = self.unique_engines()
        if engine is not None and engine not in engines:
            engines.insert(0, engine)
        if not engines:
            return

        snapshots = {}
        for current in engines:
            board, black_captures, white_captures = current.showboard()
            if (board is None or len(board) != self.board_size or
                    any(len(row) != self.board_size or
                        any(stone not in (0, 1, -1) for stone in row)
                        for row in board)):
                raise ValueError("GTP engine returned an invalid board")
            snapshots[current] = (board, black_captures, white_captures)

        selected = engine if engine is not None else engines[0]
        board, black_captures, white_captures = snapshots[selected]
        if any(snapshot != snapshots[selected] for snapshot in snapshots.values()):
            raise ValueError("GTP engines have different board positions or captures")
        self.board = [row[:] for row in board]
        self.black_captures = black_captures
        self.white_captures = white_captures
        self.draw_board()
        self.update_captures()

    def handle_click(self, event):
        """人間の手を処理"""
        if self.game_over:
            return

        # 現在の手番がAIの場合は処理しない
        if self.is_ai_turn():
            return

        # クリック位置を取得
        x = int(event.x // self.cell_size)
        y = int(event.y // self.cell_size)

        # クリック位置に着手
        if 0 <= x < self.board_size and 0 <= y < self.board_size:
            if self.is_human_match():
                previous_board = self.board_history[-2] if len(self.board_history) >= 2 else None
                result = play_move(
                    self.board, x, y, self.current_turn,
                    previous_board=previous_board,
                )
                if not result.legal:
                    reason_labels = {
                        OUT_OF_BOUNDS: "This point is outside the board.",
                        OCCUPIED: "A stone is already on this point.",
                        SUICIDE: "A suicide move is not allowed.",
                        KO: "This move is prohibited by the ko rule.",
                    }
                    messagebox.showerror(
                        "Invalid Move",
                        reason_labels.get(result.reason, "This move is not allowed."),
                    )
                    return

                self.board = result.board
                if self.current_turn == 1:
                    self.white_captures += result.captured
                else:
                    self.black_captures += result.captured
                self.board_history.append([row[:] for row in self.board])
                self.draw_board()
                self.update_captures()

            # 使用中の全エンジンに人間の手を送信する。
            elif self.ai_engines and self.board[y][x] == 0:
                color = "black" if self.current_turn == 1 else "white"

                if x > 7:
                    offset_x = x + 1
                else:
                    offset_x = x

                vertex = f"{chr(97+offset_x)}{self.board_size-y}"
                engines = self.unique_engines()
                accepted = 0
                try:
                    for engine in engines:
                        if not engine.play(color, vertex):
                            raise ValueError("GTP engine rejected the move")
                        accepted += 1
                except Exception as error:
                    if accepted:
                        self.stop_on_ai_error(f"GTP engines are out of sync: {error}")
                    else:
                        messagebox.showerror("Invalid Move", "This move is not allowed.")
                    return

                try:
                    self.update_board_from_gtp(engines[0])
                except Exception as error:
                    self.stop_on_ai_error(f"Could not synchronize the boards: {error}")
                    return

            else:
                return

            # パスの状態をリセット
            self.last_move_was_pass = False

            # ターン終了
            self.current_turn *= -1
            self.update_button_states()
            self.root.update()
            self.check_ai_turn()

    def check_ai_turn(self):
        """AIの手番をチェックして実行"""
        if self.game_over:
            return

        if self.is_ai_turn():
            # AI同士でも再帰呼び出しにならないようイベントループへ戻す。
            self.root.after(10, self.ai_turn)

    def ai_turn(self):
        """AIの手番を実行"""
        if self.game_over:
            return
        engine = self.ai_engines.get(self.current_turn)
        if not engine:
            return

        # GTPエンジンに次の手を問い合わせる。例外はTkのイベントループへ漏らさない。
        color = "black" if self.current_turn == 1 else "white"
        try:
            response = engine.genmove(color)
        except Exception as error:
            self.stop_on_ai_error(f"AI could not generate a move: {error}")
            return
        if not isinstance(response, str) or not response.strip():
            self.stop_on_ai_error("AI returned an empty or invalid move.")
            return
        response = response.strip().lower()
        
        if response == "pass":
            try:
                for other in self.unique_engines():
                    if other is not engine and not other.play(color, "pass"):
                        raise ValueError("The other engine rejected the AI pass.")
                self.update_board_from_gtp(engine)
            except Exception as error:
                self.stop_on_ai_error(str(error))
                return
            self.handle_pass(self.current_turn, send_to_engines=False)
            return
            
        if response == "resign":
            self.handle_resign(self.current_turn)
            return
        
        if response:
            try:
                # 座標を検証してから他エンジンへ転送する。
                column = response[0]
                if column < "a" or column > "t" or column == "i":
                    raise ValueError("Invalid GTP coordinate")
                x = ord(column) - ord("a") - (1 if column > "i" else 0)
                y = self.board_size - int(response[1:])
                if not (0 <= x < self.board_size and 0 <= y < self.board_size):
                    raise ValueError("GTP coordinate is outside the board")
                for other in self.unique_engines():
                    if other is not engine and not other.play(color, response):
                        raise ValueError("The other engine rejected the AI move.")
            except (ValueError, TypeError, IndexError) as error:
                self.stop_on_ai_error(f"AI returned an invalid move ({response}): {error}")
                return
            except Exception as error:
                self.stop_on_ai_error(f"Could not synchronize the AI move: {error}")
                return
            
            if 0 <= x < self.board_size and 0 <= y < self.board_size:
                
                # GTPの盤面状態を反映
                try:
                    self.update_board_from_gtp(engine)
                except Exception as error:
                    self.stop_on_ai_error(f"Could not read the AI board: {error}")
                    return

                # パスの状態をリセット
                self.last_move_was_pass = False

                # ターン終了
                self.current_turn *= -1
                self.update_button_states()
                self.root.update()
                self.check_ai_turn()

    def stop_on_ai_error(self, detail):
        """AI障害時に対局を停止し、メインスレッド上で理由を表示する。"""
        self.game_over = True
        self.update_button_states()
        messagebox.showerror("AI Error", detail)

    def update_captures(self):
        """アゲハマを更新"""
        # 白の情報（左上）
        white_info = f"White ({self.white_type})"
        self.white_label.config(text=white_info)
        
        # 白のアゲハマ表示をクリア
        self.white_captures_canvas.delete("all")
        # アゲハマを石の画像で表示（常に表示）
        self.white_captures_canvas.create_image(self.cell_size * 0.5, self.cell_size * 0.5, image=self.black_stone_img)
        self.white_captures_canvas.create_text(self.cell_size * 1.2, self.cell_size * 0.5, 
                                             text=f"× {self.black_captures}", 
                                             font=("Arial", 14))

        # 黒の情報（右下）
        black_info = f"Black ({self.black_type})"
        self.black_label.config(text=black_info)
        
        # 黒のアゲハマ表示をクリア
        self.black_captures_canvas.delete("all")
        # アゲハマを石の画像で表示（常に表示）
        self.black_captures_canvas.create_image(self.cell_size * 0.5, self.cell_size * 0.5, image=self.white_stone_img)
        self.black_captures_canvas.create_text(self.cell_size * 1.2, self.cell_size * 0.5, 
                                             text=f"× {self.white_captures}", 
                                             font=("Arial", 14))

    def update_turn_indicators(self):
        """手番表示を更新"""
        # 手番表示をクリア
        self.turn_indicator.delete("all")
        self.turn_indicator2.delete("all")

        # 現在の手番に応じて緑の線を描画（位置は固定）
        if self.current_turn == -1:  # 白の手番
            self.turn_indicator.create_line(0, 10, 40, 10, fill="green", width=5)
        else:  # 黒の手番
            self.turn_indicator2.create_line(0, 10, 40, 10, fill="green", width=5)

    def update_button_states(self):
        """ボタンの有効/無効状態を更新"""
        if self.game_over:
            # ゲーム終了時は全てのボタンを非表示
            self.white_pass_button.pack_forget()
            self.white_resign_button.pack_forget()
            self.black_pass_button.pack_forget()
            self.black_resign_button.pack_forget()
            return

        # 白のボタン表示制御
        if -1 in self.ai_engines:
            self.white_pass_button.pack_forget()
            self.white_resign_button.pack_forget()
        else:
            self.white_pass_button.pack(pady=2)
            self.white_resign_button.pack(pady=2)
            if self.current_turn == -1:
                self.white_pass_button.config(state="normal")
                self.white_resign_button.config(state="normal")
            else:
                self.white_pass_button.config(state="disabled")
                self.white_resign_button.config(state="disabled")

        # 黒のボタン表示制御
        if 1 in self.ai_engines:
            self.black_pass_button.pack_forget()
            self.black_resign_button.pack_forget()
        else:
            self.black_pass_button.pack(pady=2)
            self.black_resign_button.pack(pady=2)
            if self.current_turn == 1:
                self.black_pass_button.config(state="normal")
                self.black_resign_button.config(state="normal")
            else:
                self.black_pass_button.config(state="disabled")
                self.black_resign_button.config(state="disabled")

        # 手番表示を更新
        self.update_turn_indicators()

    def handle_pass(self, player, send_to_engines=True):
        """パスを処理"""
        if self.game_over or self.current_turn != player:
            return

        # 対局に参加する全GTPエンジンへパスを送信
        if send_to_engines and self.ai_engines:
            color = "black" if player == 1 else "white"
            try:
                for engine in self.unique_engines():
                    if not engine.play(color, "pass"):
                        raise ValueError("GTP engine rejected the pass")
                self.update_board_from_gtp(self.unique_engines()[0])
            except Exception as error:
                self.stop_on_ai_error(f"Could not synchronize the pass: {error}")
                return

        if self.last_move_was_pass:
            self.game_over = True
            self.show_final_score()
        else:
            self.last_move_was_pass = True
            if self.is_human_match():
                # パスも一手として履歴に残すと、パス後の劫取りを許可できる。
                self.board_history.append([row[:] for row in self.board])
            self.current_turn *= -1
            self.draw_board()
            self.update_button_states()
            self.check_ai_turn()

    def handle_resign(self, player):
        """投了を処理"""
        if self.game_over or self.current_turn != player:
            return

        self.game_over = True
        winner = "White" if player == 1 else "Black"
        messagebox.showinfo("Game Over", f"{'Black' if player == 1 else 'White'} resigned.\n{winner} won!")
        self.update_button_states()

    def show_final_score(self):
        """最終スコアを表示"""
        if self.ai_engines and not self.is_human_match():
            # KataGoにスコアを問い合わせ
            score_response = self.unique_engines()[0].get_final_score()
            if score_response:
                messagebox.showinfo("Game Over", f"Both players passed.\n\nFinal score: {score_response}")
                self.update_button_states()
                return

        # Human vs Human は rules.py で地とアゲハマを計算する。
        black_score, white_score = calculate_score_japanese(
            self.board,
            self.komi,
            self.black_captures,
            self.white_captures,
        )
        
        winner = "Black" if black_score > white_score else "White"
        messagebox.showinfo("Game Over", f"Both players passed.\n\n"
                                        f"Black: {black_score:.1f} points\n"
                                        f"White: {white_score:.1f} points\n\n"
                                        f"{winner} won!")
        self.update_button_states()

    def __del__(self):
        """デストラクタ"""
        pass  # GTPClientの終了はmain.pyで行う
