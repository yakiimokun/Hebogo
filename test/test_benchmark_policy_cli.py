"""ベンチマークのモデル選択と係数指定を確認する。"""

import io
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from scripts import benchmark_policy


class BenchmarkPolicyCLITest(unittest.TestCase):
    def test_policy_value_options_reach_engine_and_result_is_printed(self):
        policy = MagicMock()
        policy.ai.policy_weight = 2.0
        policy.ai.value_weight = 0.25
        result = SimpleNamespace(
            games=2, wins=1, losses=1, draws=0, unresolved=0,
            win_rate=0.5, policy_passes=3, opponent_passes=1,
            policy_seconds_per_move=0.12, opponent_seconds_per_move=0.34,
            policy_move_times=(0.12,), opponent_move_times=(0.34,),
        )
        output = io.StringIO()
        with patch.object(benchmark_policy, "PolicyGTPEngine", return_value=policy) as engine, \
             patch.object(benchmark_policy, "run_benchmark", return_value=result) as run, \
             patch("sys.stdout", output):
            status = benchmark_policy.main([
                "--policy-model", "policy.pt", "--value-model", "value.pt",
                "--policy-weight", "2", "--value-weight", "0.25",
                "--board-size", "19", "--games", "2",
            ])

        self.assertEqual(status, 0)
        self.assertEqual(engine.call_args.kwargs["board_size"], 19)
        self.assertEqual(engine.call_args.kwargs["policy_weight"], 2.0)
        self.assertEqual(engine.call_args.kwargs["value_weight"], 0.25)
        self.assertEqual(str(engine.call_args.kwargs["value_model_path"]), "value.pt")
        self.assertEqual(run.call_args.kwargs["board_size"], 19)
        self.assertEqual(run.call_args.args[3], 19 ** 2 * 3)
        self.assertIn("PASS回数 PolicyValue AI: 3 / random: 1", output.getvalue())

    def test_weights_need_value_model(self):
        with patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit) as error:
            benchmark_policy.main(["--policy-model", "policy.pt", "--value-weight", "0.1"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
