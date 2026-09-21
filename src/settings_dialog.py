from tkinter import ttk
from tkinter import Toplevel
import tkinter.messagebox as messagebox

class SettingsDialog:
    def __init__(self, parent):
        self.result = None
        
        # ダイアログウィンドウの設定
        self.dialog = Toplevel(parent)
        self.dialog.title("match configuration")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.wm_attributes("-topmost", True)  # ダイアログを最前面に表示
        
        # ウィンドウサイズと位置の設定
        width = 300
        height = 400  # 高さを増やして新しい設定を追加
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # 盤面サイズの設定
        ttk.Label(self.dialog, text="board size:").pack(pady=10)
        self.board_size = ttk.Combobox(self.dialog, values=[9, 13, 19], state="readonly")
        self.board_size.set(19)
        self.board_size.pack(pady=5)
        
        # コミの設定
        ttk.Label(self.dialog, text="komi:").pack(pady=10)
        self.komi = ttk.Entry(self.dialog)
        self.komi.insert(0, "6.5")
        self.komi.pack(pady=5)
        
        # 黒番の設定
        ttk.Label(self.dialog, text="black:").pack(pady=10)
        self.black_type = ttk.Combobox(
            self.dialog, values=["player", "Random AI", "Policy AI", "KataGo"], state="readonly"
        )
        self.black_type.set("player")
        self.black_type.pack(pady=5)
        
        # 白番の設定
        ttk.Label(self.dialog, text="white:").pack(pady=10)
        self.white_type = ttk.Combobox(
            self.dialog, values=["player", "Random AI", "Policy AI", "KataGo"], state="readonly"
        )
        self.white_type.set("Random AI")
        self.white_type.pack(pady=5)
        
        # 決定ボタン
        ttk.Button(self.dialog, text="start", command=self.on_ok).pack(pady=20)
        
        # ダイアログが閉じられるまで待機
        parent.wait_window(self.dialog)
    
    def on_ok(self):
        try:
            board_size = int(self.board_size.get())
            komi = float(self.komi.get())
            black_type = self.black_type.get()
            white_type = self.white_type.get()
            
            self.result = {
                "board_size": board_size,
                "komi": komi,
                "black_type": black_type,
                "white_type": white_type
            }
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("error", "invalid value")
