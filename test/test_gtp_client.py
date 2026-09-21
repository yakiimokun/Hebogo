"""KataGo の GTP 応答と showboard の読み取りを確認する。"""

import io
import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from src.gtp_client import GTPClient


class GTPClientTest(unittest.TestCase):
    def test_reads_complete_responses_until_blank_line(self):
        output = (
            "= D10\n\n"
            "= pass\n\n"
            "= resign\n\n"
            "= W+2.5\n\n"
            "? illegal move\nsecond detail\n\n"
            "=\nA B C\n3 X . O\n2 . . .\n1 . . .\n\n"
        )
        client = GTPClient.__new__(GTPClient)
        client.process = SimpleNamespace(stdout=io.StringIO(output))
        client.response_queue = queue.Queue()
        client.running = True

        client._read_responses()

        self.assertEqual(client.response_queue.get_nowait(), "D10")
        self.assertEqual(client.response_queue.get_nowait(), "pass")
        self.assertEqual(client.response_queue.get_nowait(), "resign")
        self.assertEqual(client.response_queue.get_nowait(), "W+2.5")
        self.assertIsNone(client.response_queue.get_nowait())
        self.assertIn("3 X . O", client.response_queue.get_nowait())

    def test_process_exit_notifies_waiter(self):
        client = GTPClient.__new__(GTPClient)
        client.process = SimpleNamespace(stdout=io.StringIO("= D10\n"))
        client.response_queue = queue.Queue()
        client.running = True

        client._read_responses()

        self.assertFalse(client.running)
        self.assertIsNone(client.response_queue.get_nowait())

    def test_showboard_parses_rows_and_captures(self):
        rows = []
        for number in range(9, 0, -1):
            stones = ["."] * 9
            if number == 9:
                stones = ["X1X"] + ["."] * 7
            if number == 8:
                stones[3] = "O2"
            rows.append(f"{number} {' '.join(stones)} {number}")
        response = "A B C D E F G H J\n" + "\n".join(rows)
        response += "\nB stones captured: 2\nW stones captured: 1"
        client = GTPClient.__new__(GTPClient)
        client.board_size = 9
        client.send_command = Mock(return_value=response)

        board, black_captures, white_captures = client.showboard()

        self.assertEqual(len(board), 9)
        self.assertEqual(board[0][0], 1)
        self.assertEqual(board[0][1], 1)
        self.assertEqual(board[1][3], -1)
        self.assertEqual((black_captures, white_captures), (2, 1))
        client.send_command.assert_called_once_with("showboard")

    def test_showboard_rejects_incomplete_board(self):
        client = GTPClient.__new__(GTPClient)
        client.board_size = 9
        client.send_command = Mock(return_value="A B C D E F G H J\n9 X . . . . . . . .")

        with self.assertRaisesRegex(ValueError, "incomplete"):
            client.showboard()

    def test_send_command_does_not_wait_after_process_exit(self):
        client = GTPClient.__new__(GTPClient)
        client.command_lock = threading.Lock()
        client.command_queue = queue.Queue()
        client.process = SimpleNamespace(poll=lambda: 1)
        client.running = True

        self.assertIsNone(client.send_command("genmove black"))
        self.assertTrue(client.command_queue.empty())


if __name__ == "__main__":
    unittest.main()
