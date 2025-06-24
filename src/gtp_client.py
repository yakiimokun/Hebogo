import subprocess
import threading
import queue
import time

class GTPClient:
    def __init__(self, katago_path, model_path, config_path):
        """KataGoのGTPプロセスを初期化"""
        self.process = subprocess.Popen(
            [katago_path, "gtp", "-model", model_path, "-config", config_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.running = True
        
        # レスポンス読み取りスレッドを開始
        self.reader_thread = threading.Thread(target=self._read_responses)
        self.reader_thread.daemon = True
        self.reader_thread.start()
        
        # コマンド送信スレッドを開始
        self.writer_thread = threading.Thread(target=self._write_commands)
        self.writer_thread.daemon = True
        self.writer_thread.start()

    def _read_responses(self):
        """KataGoからのレスポンスを読み取る"""
        while self.running:
            line = self.process.stdout.readline()
            print("{}".format(line))
            if not line:
                break

            if line.startswith('='):
                if line.endswith('\n'):
                    if len(line) == 3:
                        self.response_queue.put('') # 空文字列を返して成功を示す
                        continue

                    if len(line) == 5:
                        self.response_queue.put(line[2:].strip()) 
                        continue

                    if "pass" in line:
                        self.response_queue.put('pass')
                        continue

                    if "resign" in line:
                        self.response_queue.put('resign')
                        continue

                # 複数行のレスポンスを収集
                response_lines = [line[1:].strip()]
                while True:
                    next_line = self.process.stdout.readline()
                    #print("{}".format(next_line))
                    response_lines.append(next_line.strip())
                    if next_line.startswith('W stones captured:'):  # showboardの終わり
                        break
                # 収集したレスポンスを投入（成功を示す）
                self.response_queue.put('\n'.join(response_lines))
                continue
            elif line.startswith('?'):
                self.response_queue.put(None)  # エラーを示す

    def _write_commands(self):
        """KataGoにコマンドを送信"""
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=0.1)
                self.process.stdin.write(cmd + '\n')
                self.process.stdin.flush()
            except queue.Empty:
                continue

    def send_command(self, command):
        """GTPコマンドを送信し、レスポンスを待つ"""
        self.command_queue.put(command)
        return self.response_queue.get()

    def close(self):
        """プロセスを終了"""
        self.running = False
        self.process.terminate()
        self.process.wait()
        self.reader_thread.join()
        self.writer_thread.join()

    def genmove(self, color):
        """指定された色の手を生成"""
        response = self.send_command(f"genmove {color}")
        if response:
            return response.lower()
        return None

    def play(self, color, vertex):
        """指定された位置に石を打つ"""
        response = self.send_command(f"play {color} {vertex}")
        return response is not None

    def clear_board(self):
        """盤面をクリア"""
        return self.send_command("clear_board") is not None

    def set_board_size(self, size):
        """盤面サイズを設定"""
        return self.send_command(f"boardsize {size}") is not None

    def komi(self, value):
        """コミを設定"""
        return self.send_command(f"komi {value}") is not None

    def get_final_score(self):
        """最終スコアを取得"""
        return self.send_command("final_score")

    def showboard(self):
        """現在の盤面状態を取得"""
        response = self.send_command("showboard")
        if not response:
            return None, 0, 0  # board, black_captures, white_captures

        # 盤面の状態を解析
        board = []
        black_captures = 0
        white_captures = 0
        parsing_board = False
        
        for line in response.split('\n'):
            if line.startswith('='):
                continue
            if line.startswith('B stones captured:'):
                black_captures = int(line.split()[-1])
            elif line.startswith('W stones captured:'):
                white_captures = int(line.split()[-1])
            elif line.startswith('A B C D E F G H J'):
                parsing_board = True
                continue
            elif parsing_board and line.strip():
                # 盤面の行を解析
                row = []
                for char in line[2:]:  # 行番号をスキップ
                    if char == 'X':
                        row.append(1)  # 黒
                    elif char == 'O':
                        row.append(-1)  # 白
                    elif char == '.':
                        row.append(0)  # 空点
                if row:  # 空行でない場合のみ追加
                    board.append(row)
            elif parsing_board and not line.strip():
                parsing_board = False

        return board, black_captures, white_captures

    def is_resign(self, move):
        """投了かどうかを判定"""
        return move and move.lower() == "resign"

    def is_pass(self, move):
        """パスかどうかを判定"""
        return move and move.lower() == "pass" 