"""対局結果と着手時間の集計を確認する。"""

import unittest
from unittest.mock import patch

from src.benchmark import run_benchmark
from src.gtp_match import GTPMatch


class PassEngine:
    def __init__(self):
        self.closed = False

    def send_command(self, command):
        if command.startswith("genmove"):
            return "pass"
        if command == "final_score":
            return "W+6.5"
        return ""

    def close(self):
        self.closed = True


class BenchmarkTest(unittest.TestCase):
    def test_times_only_genmove(self):
        with patch("src.gtp_match.perf_counter", side_effect=[1.0, 1.2, 2.0, 2.3]):
            result = GTPMatch(PassEngine(), PassEngine(), board_size=9).play()
        self.assertEqual(result.reason, "two_passes")
        self.assertAlmostEqual(result.move_times[0][1], 0.2)
        self.assertAlmostEqual(result.move_times[1][1], 0.3)

    def test_alternates_colors_and_reports_decided_win_rate(self):
        opponents = []

        def factory(index):
            opponent = PassEngine()
            opponents.append(opponent)
            return opponent

        with patch("src.gtp_match.perf_counter", side_effect=range(8)):
            result = run_benchmark(PassEngine(), factory, games=2)
        self.assertEqual((result.wins, result.losses, result.draws, result.unresolved), (1, 1, 0, 0))
        self.assertEqual(result.win_rate, 0.5)
        self.assertEqual(result.policy_seconds_per_move, 1.0)
        self.assertEqual(len(result.policy_move_times), 2)
        self.assertTrue(all(engine.closed for engine in opponents))

    def test_move_limit_is_unresolved(self):
        with patch("src.gtp_match.perf_counter", side_effect=[0.0, 0.1]):
            result = run_benchmark(PassEngine(), lambda index: PassEngine(), games=1, max_moves=1)
        self.assertEqual(result.unresolved, 1)
        self.assertIsNone(result.win_rate)


if __name__ == "__main__":
    unittest.main()
