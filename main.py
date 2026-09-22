from tkinter import Tk
import tkinter.messagebox as messagebox
from src import GoGameApp
from src.settings_dialog import SettingsDialog
from src.gtp_client import GTPClient
from src.random_gtp_engine import RandomGTPEngine
import os
import json


def model_path_for_size(config, board_size, name):
    """盤面サイズ別の重みを優先し、単一パス設定にも対応する。"""
    paths_key = f"{name}_model_paths"
    paths = config.get(paths_key)
    if paths is not None:
        if not isinstance(paths, dict):
            raise ValueError(f"{paths_key} must be an object")
        path = paths.get(str(board_size))
        if path is not None:
            if not isinstance(path, str) or not path.strip():
                raise ValueError(f"Invalid {name} model path for {board_size}x{board_size}")
            return path
    return config.get(f"{name}_model_path")


def policy_model_path_for_size(config, board_size):
    return model_path_for_size(config, board_size, "policy")


def value_model_path_for_size(config, board_size):
    return model_path_for_size(config, board_size, "value")


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
    
    # 外部モデルを使うAIが選択された場合だけ設定を読む。
    player_types = (settings.result["black_type"], settings.result["white_type"])
    katago_client = None
    policy_engine = None
    config = {}
    if "KataGo" in player_types or "PolicyValue AI" in player_types:
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
        except (OSError, json.JSONDecodeError) as error:
            messagebox.showerror("error", f"Failed to load config.json: {error}")
            root.destroy()
            return

    if "KataGo" in player_types:
        try:
            katago_config = config["katago"]
            katago_path = katago_config["binary_path"]
            model_path = katago_config["model_path"]
            config_path = katago_config["config_path"]
        except (KeyError, TypeError) as error:
            messagebox.showerror("error", f"Missing KataGo setting in config.json: {error}")
            root.destroy()
            return

        if not all(isinstance(path, str) and path.strip() for path in
                   (katago_path, model_path, config_path)):
            messagebox.showerror("error", "Invalid KataGo path in config.json")
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
            katago_client.close()
            root.destroy()
            return
        
        if not katago_client.komi(settings.result["komi"]):
            messagebox.showerror("error", "Failed to set komi")
            katago_client.close()
            root.destroy()
            return

    if "PolicyValue AI" in player_types:
        try:
            policy_model_path = policy_model_path_for_size(config, settings.result["board_size"])
            value_model_path = value_model_path_for_size(config, settings.result["board_size"])
        except ValueError as error:
            messagebox.showerror("PolicyValue AI Error", str(error))
            if katago_client:
                katago_client.close()
            root.destroy()
            return
        if not isinstance(policy_model_path, str) or not policy_model_path.strip():
            messagebox.showerror("PolicyValue AI Error", "Set policy_model_paths or policy_model_path in config.json for this board size.")
            if katago_client:
                katago_client.close()
            root.destroy()
            return
        if not os.path.isfile(policy_model_path):
            messagebox.showerror("PolicyValue AI Error", f"Policy model file not found: {policy_model_path}")
            if katago_client:
                katago_client.close()
            root.destroy()
            return
        if not isinstance(value_model_path, str) or not value_model_path.strip():
            messagebox.showerror("PolicyValue AI Error", "Set value_model_paths or value_model_path in config.json for this board size.")
            if katago_client:
                katago_client.close()
            root.destroy()
            return
        if not os.path.isfile(value_model_path):
            messagebox.showerror("PolicyValue AI Error", f"Value model file not found: {value_model_path}")
            if katago_client:
                katago_client.close()
            root.destroy()
            return
        try:
            # 通常のGUI起動ではPyTorchを読み込まない。
            from src.policy_gtp_engine import PolicyGTPEngine

            policy_engine = PolicyGTPEngine(
                board_size=settings.result["board_size"],
                komi=settings.result["komi"],
                model_path=policy_model_path,
                value_model_path=value_model_path,
            )
        except Exception as error:
            messagebox.showerror("PolicyValue AI Error", f"Could not load PolicyValue AI models: {error}")
            if katago_client:
                katago_client.close()
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
        elif player_type == "PolicyValue AI":
            ai_engines[color] = policy_engine

    try:
        GoGameApp(
            root,
            board_size=settings.result["board_size"],
            komi=settings.result["komi"],
            black_type=settings.result["black_type"],
            white_type=settings.result["white_type"],
            gtp_client=katago_client,
            ai_engines=ai_engines,
        )
        root.mainloop()
    finally:
        # 対局終了時には外部プロセス・エンジンを確実に閉じる。
        for engine in dict.fromkeys(ai_engines.values()):
            close = getattr(engine, "close", None)
            if close:
                close()

if __name__ == "__main__":
    main()
