"""碁盤の星と天元の描画を確認する。"""

import unittest
from unittest.mock import MagicMock

from src.go_game_app import GoGameApp


class BoardLayoutTest(unittest.TestCase):
    def make_app(self, size):
        app = GoGameApp.__new__(GoGameApp)
        app.board_size = size
        app.cell_size = 40
        app.board = [[0] * size for _ in range(size)]
        app.canvas = MagicMock()
        return app

    def test_19_line_board_has_eight_stars_and_tengen(self):
        app = self.make_app(19)

        app.draw_board()

        self.assertEqual(app.canvas.create_oval.call_count, 9)
        centers = {
            ((call.args[0] + call.args[2]) / 2,
             (call.args[1] + call.args[3]) / 2)
            for call in app.canvas.create_oval.call_args_list
        }
        expected = {(40 * (x + 0.5), 40 * (y + 0.5))
                    for x in (3, 9, 15) for y in (3, 9, 15)}
        self.assertEqual(centers, expected)

    def test_9_line_board_does_not_receive_19_line_stars(self):
        app = self.make_app(9)

        app.draw_board()

        app.canvas.create_oval.assert_not_called()


if __name__ == "__main__":
    unittest.main()
