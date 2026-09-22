"""PolicyValue AIの設定・GUI連携を表示環境なしで確認する。"""

import json
import sys
import types
import unittest
from unittest.mock import MagicMock, mock_open, patch

import main
from src.go_game_app import GoGameApp
from src.settings_dialog import SettingsDialog


class PolicyGUIStartupTest(unittest.TestCase):
    def setUp(self):
        self.root = MagicMock()
        self.settings = MagicMock()
        self.settings.result = {
            "board_size": 9,
            "komi": 6.5,
            "black_type": "player",
            "white_type": "PolicyValue AI",
        }

    def test_policy_model_is_loaded_only_when_selected(self):
        fake_engine = MagicMock()
        engine_class = MagicMock(return_value=fake_engine)
        module = types.ModuleType("src.policy_gtp_engine")
        module.PolicyGTPEngine = engine_class
        with patch.object(main, "Tk", return_value=self.root), \
             patch.object(main, "SettingsDialog", return_value=self.settings), \
             patch.object(main, "GoGameApp") as app_class, \
             patch.object(main.os.path, "isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps({"policy_model_path": "model.pt", "value_model_path": "value.pt"}))), \
             patch.dict(sys.modules, {"src.policy_gtp_engine": module}):
            main.main()

        engine_class.assert_called_once_with(board_size=9, komi=6.5, model_path="model.pt", value_model_path="value.pt")
        self.assertIs(app_class.call_args.kwargs["ai_engines"][-1], fake_engine)
        fake_engine.close.assert_called_once()

    def test_selects_model_for_board_size(self):
        fake_engine = MagicMock()
        engine_class = MagicMock(return_value=fake_engine)
        module = types.ModuleType("src.policy_gtp_engine")
        module.PolicyGTPEngine = engine_class
        config = {
            "policy_model_path": "old_19.pt",
            "policy_model_paths": {"9": "model_9.pt", "19": "model_19.pt"},
            "value_model_path": "old_value_19.pt",
            "value_model_paths": {"9": "value_9.pt", "19": "value_19.pt"},
        }
        with patch.object(main, "Tk", return_value=self.root), \
             patch.object(main, "SettingsDialog", return_value=self.settings), \
             patch.object(main, "GoGameApp"), \
             patch.object(main.os.path, "isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps(config))), \
             patch.dict(sys.modules, {"src.policy_gtp_engine": module}):
            main.main()
        engine_class.assert_called_once_with(board_size=9, komi=6.5, model_path="model_9.pt", value_model_path="value_9.pt")

    def test_missing_model_setting_shows_error_and_does_not_start_game(self):
        with patch.object(main, "Tk", return_value=self.root), \
             patch.object(main, "SettingsDialog", return_value=self.settings), \
             patch.object(main, "GoGameApp") as app_class, \
             patch.object(main.messagebox, "showerror") as showerror, \
             patch("builtins.open", mock_open(read_data="{}")):
            main.main()

        self.assertIn("policy_model_path", showerror.call_args.args[1])
        app_class.assert_not_called()
        self.root.destroy.assert_called_once()

    def test_model_load_failure_shows_error_and_does_not_start_game(self):
        module = types.ModuleType("src.policy_gtp_engine")
        module.PolicyGTPEngine = MagicMock(side_effect=ValueError("bad checkpoint"))
        with patch.object(main, "Tk", return_value=self.root), \
             patch.object(main, "SettingsDialog", return_value=self.settings), \
             patch.object(main, "GoGameApp") as app_class, \
             patch.object(main.messagebox, "showerror") as showerror, \
             patch.object(main.os.path, "isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps({"policy_model_path": "bad.pt", "value_model_path": "value.pt"}))), \
             patch.dict(sys.modules, {"src.policy_gtp_engine": module}):
            main.main()

        self.assertIn("bad checkpoint", showerror.call_args.args[1])
        app_class.assert_not_called()
        self.root.destroy.assert_called_once()

    def test_missing_value_model_stops_startup(self):
        with patch.object(main, "Tk", return_value=self.root), \
             patch.object(main, "SettingsDialog", return_value=self.settings), \
             patch.object(main, "GoGameApp") as app_class, \
             patch.object(main.messagebox, "showerror") as showerror, \
             patch.object(main.os.path, "isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps({"policy_model_path": "model.pt"}))):
            main.main()

        self.assertIn("value_model_path", showerror.call_args.args[1])
        app_class.assert_not_called()
        self.root.destroy.assert_called_once()

    def test_human_match_does_not_open_config(self):
        self.settings.result["white_type"] = "player"
        with patch.object(main, "Tk", return_value=self.root), \
             patch.object(main, "SettingsDialog", return_value=self.settings), \
             patch.object(main, "GoGameApp"), \
             patch("builtins.open") as open_file:
            main.main()

        open_file.assert_not_called()


class KataGoConfigTest(unittest.TestCase):
    def setUp(self):
        self.root = MagicMock()
        self.settings = MagicMock()
        self.settings.result = {
            "board_size": 9,
            "komi": 6.5,
            "black_type": "player",
            "white_type": "KataGo",
        }

    def test_reads_katago_paths_from_nested_config(self):
        config = {
            "katago": {
                "binary_path": "/path/to/katago",
                "model_path": "/path/to/model.bin.gz",
                "config_path": "/path/to/gtp_setting.cfg",
            }
        }
        with patch.object(main, "Tk", return_value=self.root), \
             patch.object(main, "SettingsDialog", return_value=self.settings), \
             patch.object(main, "GTPClient") as client_class, \
             patch.object(main, "GoGameApp") as app_class, \
             patch.object(main.os.path, "exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps(config))):
            main.main()

        client_class.assert_called_once_with(
            "/path/to/katago", "/path/to/model.bin.gz", "/path/to/gtp_setting.cfg"
        )
        self.assertIs(app_class.call_args.kwargs["ai_engines"][-1], client_class.return_value)
        client_class.return_value.close.assert_called_once()

    def test_missing_or_invalid_katago_object_stops_startup(self):
        for config in ({}, {"katago": {}}, {"katago": []},
                       {"katago": {"binary_path": None, "model_path": "m", "config_path": "c"}}):
            with self.subTest(config=config), \
                 patch.object(main, "Tk", return_value=self.root), \
                 patch.object(main, "SettingsDialog", return_value=self.settings), \
                 patch.object(main, "GTPClient") as client_class, \
                 patch.object(main, "GoGameApp") as app_class, \
                 patch.object(main.messagebox, "showerror") as showerror, \
                 patch("builtins.open", mock_open(read_data=json.dumps(config))):
                main.main()

            showerror.assert_called_once()
            client_class.assert_not_called()
            app_class.assert_not_called()


class PolicySettingsTest(unittest.TestCase):
    def test_both_color_selectors_offer_policy_value_ai(self):
        parent = MagicMock()
        with patch("src.settings_dialog.Toplevel"), \
             patch("src.settings_dialog.ttk.Combobox") as combo:
            SettingsDialog(parent)

        player_selectors = [
            call.kwargs["values"] for call in combo.call_args_list
            if "player" in call.kwargs["values"]
        ]
        self.assertEqual(len(player_selectors), 2)
        self.assertTrue(all("PolicyValue AI" in values for values in player_selectors))


class PolicyGUITurnTest(unittest.TestCase):
    def setUp(self):
        self.app = GoGameApp.__new__(GoGameApp)
        self.app.game_over = False
        self.app.current_turn = -1
        self.app.board_size = 9
        self.app.root = MagicMock()
        self.app.update_button_states = MagicMock()
        self.engine = MagicMock()
        self.app.ai_engines = {-1: self.engine}

    def test_inference_exception_stops_game_without_propagating(self):
        self.engine.genmove.side_effect = RuntimeError("model failed")
        with patch("src.go_game_app.messagebox.showerror") as showerror:
            self.app.ai_turn()

        self.assertTrue(self.app.game_over)
        self.assertIn("model failed", showerror.call_args.args[1])
        self.app.update_button_states.assert_called_once()

    def test_malformed_gtp_move_stops_game(self):
        self.engine.genmove.return_value = "not-a-coordinate"
        with patch("src.go_game_app.messagebox.showerror") as showerror:
            self.app.ai_turn()

        self.assertTrue(self.app.game_over)
        self.assertIn("invalid move", showerror.call_args.args[1])

    def test_board_read_failure_stops_game(self):
        self.engine.genmove.return_value = "a1"
        self.app.update_board_from_gtp = MagicMock(side_effect=RuntimeError("showboard failed"))
        with patch("src.go_game_app.messagebox.showerror") as showerror:
            self.app.ai_turn()

        self.assertTrue(self.app.game_over)
        self.assertIn("showboard failed", showerror.call_args.args[1])


class MixedEngineSynchronizationTest(unittest.TestCase):
    def setUp(self):
        self.app = GoGameApp.__new__(GoGameApp)
        self.app.game_over = False
        self.app.board_size = 9
        self.app.current_turn = 1
        self.app.black_type = "KataGo"
        self.app.white_type = "PolicyValue AI"
        self.app.last_move_was_pass = False
        self.app.board = [[0] * 9 for _ in range(9)]
        self.app.root = MagicMock()
        self.app.draw_board = MagicMock()
        self.app.update_captures = MagicMock()
        self.app.update_button_states = MagicMock()
        self.app.check_ai_turn = MagicMock()
        self.katago = MagicMock()
        self.policy = MagicMock()
        self.app.ai_engines = {1: self.katago, -1: self.policy}

    def test_katago_move_is_sent_to_policy_and_drawn(self):
        board = [[0] * 9 for _ in range(9)]
        board[5][3] = 1  # D4
        self.katago.genmove.return_value = "D4"
        self.katago.showboard.return_value = (board, 0, 0)
        self.policy.showboard.return_value = (board, 0, 0)

        self.app.ai_turn()

        self.policy.play.assert_called_once_with("black", "d4")
        self.assertEqual(self.app.board[5][3], 1)
        self.app.draw_board.assert_called_once()
        self.assertEqual(self.app.current_turn, -1)

    def test_policy_move_is_sent_to_katago_and_drawn(self):
        self.app.current_turn = -1
        board = [[0] * 9 for _ in range(9)]
        board[5][3] = -1
        self.policy.genmove.return_value = "D4"
        self.policy.showboard.return_value = (board, 0, 0)
        self.katago.showboard.return_value = (board, 0, 0)

        self.app.ai_turn()

        self.katago.play.assert_called_once_with("white", "d4")
        self.assertEqual(self.app.board[5][3], -1)
        self.app.draw_board.assert_called_once()
        self.assertEqual(self.app.current_turn, 1)

    def test_different_engine_boards_stop_the_match(self):
        self.katago.genmove.return_value = "D4"
        katago_board = [[0] * 9 for _ in range(9)]
        katago_board[5][3] = 1
        self.katago.showboard.return_value = (katago_board, 0, 0)
        self.policy.showboard.return_value = ([[0] * 9 for _ in range(9)], 0, 0)

        with patch("src.go_game_app.messagebox.showerror") as showerror:
            self.app.ai_turn()

        self.assertTrue(self.app.game_over)
        self.app.draw_board.assert_not_called()
        self.assertIn("different board positions", showerror.call_args.args[1])

    def test_ai_pass_is_sent_to_other_engine(self):
        board = [[0] * 9 for _ in range(9)]
        self.katago.genmove.return_value = "pass"
        self.katago.showboard.return_value = (board, 0, 0)
        self.policy.showboard.return_value = (board, 0, 0)

        self.app.ai_turn()

        self.policy.play.assert_called_once_with("black", "pass")
        self.assertTrue(self.app.last_move_was_pass)
        self.assertEqual(self.app.current_turn, -1)

    def test_different_captures_stop_the_match(self):
        board = [[0] * 9 for _ in range(9)]
        board[5][3] = 1
        self.katago.genmove.return_value = "D4"
        self.katago.showboard.return_value = (board, 1, 0)
        self.policy.showboard.return_value = (board, 0, 0)

        with patch("src.go_game_app.messagebox.showerror") as showerror:
            self.app.ai_turn()

        self.assertTrue(self.app.game_over)
        self.assertIn("captures", showerror.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
