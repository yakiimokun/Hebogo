from tkinter import Tk
import tkinter.messagebox as messagebox
from src import GoGameApp
from src.settings_dialog import SettingsDialog
from src.gtp_client import GTPClient
from src.random_gtp_engine import RandomGTPEngine
import os
import json

def main():
    root = Tk()
    root.title("Hebogo")
    root.geometry("1x1")  # 最小サイズに設定
    root.update()  # ウィンドウを更新して位置を計算可能にする
    
    # 設定ダイアログを表示
    settings = SettingsDialog(root)
    if settings.result is None:  # キャンセルされた場合
        root.destroy()
        return
    
    # KataGoが選択された場合だけ設定を読み、プロセスを初期化する。
    player_types = (settings.result["black_type"], settings.result["white_type"])
    katago_client = None
    if "KataGo" in player_types:
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            katago_path = config["katago_path"]
            model_path = config["model_path"]
            config_path = config["config_path"]
        except (OSError, json.JSONDecodeError, KeyError) as error:
            messagebox.showerror("error", f"Failed to load config.json: {error}")
            root.destroy()
            return

        if not os.path.exists(katago_path):
            messagebox.showerror("error", "KataGo executable not found")
            root.destroy()
            return
        if not os.path.exists(model_path):
            messagebox.showerror("error", "KataGo model file not found")
            root.destroy()
            return
        if not os.path.exists(config_path):
            messagebox.showerror("error", "KataGo config file not found")
            root.destroy()
            return
            
        katago_client = GTPClient(katago_path, model_path, config_path)
        
        # 盤面サイズとコミを設定
        if not katago_client.set_board_size(settings.result["board_size"]):
            messagebox.showerror("error", "Failed to set board size")
            root.destroy()
            return
        
        if not katago_client.komi(settings.result["komi"]):
            messagebox.showerror("error", "Failed to set komi")
            root.destroy()
            return
    
    # メインウィンドウを表示してゲームを開始
    ai_engines = {}
    for color, player_type in zip((1, -1), player_types):
        if player_type == "Random AI":
            ai_engines[color] = RandomGTPEngine(
                settings.result["board_size"], settings.result["komi"]
            )
        elif player_type == "KataGo":
            ai_engines[color] = katago_client

    app = GoGameApp(
        root,
        board_size=settings.result["board_size"],
        komi=settings.result["komi"],
        black_type=settings.result["black_type"],
        white_type=settings.result["white_type"],
        gtp_client=katago_client,
        ai_engines=ai_engines,
    )
    root.mainloop()
    
    # ゲーム終了時にKataGoプロセスを終了
    if katago_client:
        katago_client.close()

if __name__ == "__main__":
    main()
