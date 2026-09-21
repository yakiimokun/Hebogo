import subprocess
import threading
import queue
import re

class GTPClient:
    def __init__(self, katago_path, model_path, config_path, response_timeout=60):
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
        self.command_lock = threading.Lock()
        self.response_timeout = response_timeout
        self.board_size = 19
        self.running = True
        
        # レスポンス読み取りスレッドを開始
        self.reader_thread = threading.Thread(target=self._read_responses)
        self.reader_thread.daemon = True
        self.reader_thread.start()
        
        # コマンド送信スレッドを開始
        self.writer_thread = threading.Thread(target=self._write_commands)
        self.writer_thread.daemon = True
        self.writer_thread.start()

        # stderr が満杯になって KataGo が停止しないよう読み捨てる。
        self.stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self.stderr_thread.start()

    def _drain_stderr(self):
        for _ in self.process.stderr:
            pass

    def _read_responses(self):
        """空行までを1件のGTP応答として読み取る。"""
        response_lines = []
        while self.running:
            line = self.process.stdout.readline()
            if not line:
                break
            if not line.strip():
                if response_lines:
                    first = response_lines[0]
                    if first.startswith('='):
                        header = first[1:]
                        # コマンドIDは送っていないが、付いていても本文と混同しない。
                        if header and header[0].isdigit():
                            header = re.sub(r'^\d+(?:\s|$)', '', header, count=1)
                        body = '\n'.join([header.lstrip()] + response_lines[1:])
                        self.response_queue.put(body.strip('\n'))
                    else:
                        self.response_queue.put(None)
                    response_lines = []
                continue
            response_lines.append(line.rstrip('\r\n'))

        self.running = False
        # 途中終了やプロセス終了を待機中の send_command に通知する。
        self.response_queue.put(None)

    def _write_commands(self):
        """KataGoにコマンドを送信"""
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=0.1)
                if cmd is None:
                    break
                self.process.stdin.write(cmd + '\n')
                self.process.stdin.flush()
            except queue.Empty:
                continue
            except (OSError, ValueError):
                self.running = False
                self.response_queue.put(None)
                break

    def send_command(self, command):
        """GTPコマンドを送信し、レスポンスを待つ"""
        with self.command_lock:
            if not self.running or self.process.poll() is not None:
                return None
            self.command_queue.put(command)
            try:
                return self.response_queue.get(timeout=self.response_timeout)
            except queue.Empty:
                self.close()
                return None

    def close(self):
        """プロセスを終了"""
        self.running = False
        self.command_queue.put(None)
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.reader_thread.join(timeout=5)
        self.writer_thread.join(timeout=5)
        self.stderr_thread.join(timeout=5)

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
        if self.send_command(f"boardsize {size}") is None:
            return False
        self.board_size = size
        return True

    def komi(self, value):
        """コミを設定"""
        return self.send_command(f"komi {value}") is not None

    def get_final_score(self):
        """最終スコアを取得"""
        return self.send_command("final_score")

    def showboard(self):
        """現在の盤面状態を取得"""
        response = self.send_command("showboard")
        if response is None:
            return None, 0, 0  # board, black_captures, white_captures

        board = [None] * self.board_size
        black_captures = 0
        white_captures = 0
        for line in response.splitlines():
            stripped = line.strip()
            if stripped.startswith('B stones captured:'):
                black_captures = int(line.split()[-1])
                continue
            if stripped.startswith('W stones captured:'):
                white_captures = int(line.split()[-1])
                continue
            row_match = re.match(r'^(\d+)\s+([.XO\d\s]+)$', stripped)
            if not row_match:
                continue
            row_number = int(row_match.group(1))
            if not 1 <= row_number <= self.board_size:
                continue
            # KataGo は直近の手番号を X1X や .1 のように重ねて表示する。
            stones = re.findall(r'[.XO]', row_match.group(2))
            if len(stones) != self.board_size:
                raise ValueError("invalid showboard row")
            index = self.board_size - row_number
            if board[index] is not None:
                raise ValueError("duplicate showboard row")
            board[index] = [{'.': 0, 'X': 1, 'O': -1}[stone] for stone in stones]

        if any(row is None for row in board):
            raise ValueError("incomplete showboard response")
        return board, black_captures, white_captures

    def is_resign(self, move):
        """投了かどうかを判定"""
        return move and move.lower() == "resign"

    def is_pass(self, move):
        """パスかどうかを判定"""
        return move and move.lower() == "pass"
