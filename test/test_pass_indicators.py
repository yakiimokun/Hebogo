"""パス表示と手番バーの更新を確認する。"""

import unittest
from unittest.mock import MagicMock

from src.go_game_app import GoGameApp


class PassIndicatorTest(unittest.TestCase):
    def setUp(self):
        self.app = GoGameApp.__new__(GoGameApp)
        self.app.background_color = "#808080"
        self.app.pass_idle_color = "#b0b0b0"
        self.app.pass_active_color = "#fff4ce"
        self.app.turn_bar_width = 56
        self.app.white_pass_label = MagicMock()
        self.app.black_pass_label = MagicMock()
        self.app.turn_indicator = MagicMock()
        self.app.turn_indicator2 = MagicMock()
        self.app.passed_players = set()

    def test_pass_label_lights_only_for_player_who_passed(self):
        self.app.passed_players.add(1)
        self.app.update_pass_labels()

        self.app.white_pass_label.config.assert_called_with(bg="#b0b0b0", fg="#505050")
        self.app.black_pass_label.config.assert_called_with(bg="#fff4ce", fg="black")

    def test_both_labels_can_light_after_consecutive_passes(self):
        self.app.passed_players.update((1, -1))
        self.app.update_pass_labels()

        self.app.white_pass_label.config.assert_called_with(bg="#fff4ce", fg="black")
        self.app.black_pass_label.config.assert_called_with(bg="#fff4ce", fg="black")

    def test_turn_bar_uses_its_full_width(self):
        self.app.current_turn = -1
        self.app.update_turn_indicators()

        self.app.turn_indicator.create_line.assert_called_once_with(
            2, 10, 54, 10, fill="green", width=5
        )


if __name__ == "__main__":
    unittest.main()
