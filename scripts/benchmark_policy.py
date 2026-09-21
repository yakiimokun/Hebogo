#!/usr/bin/env python3
"""9路 Policy AI の対戦勝率と一手の応答時間を測る。"""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.benchmark import run_benchmark  # noqa: E402
from src.policy_gtp_engine import PolicyGTPEngine  # noqa: E402
from src.random_gtp_engine import RandomGTPEngine  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-model", type=Path, required=True)
    parser.add_argument("--opponent", choices=("random", "katago"), default="random")
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--max-moves", type=int, default=243)
    parser.add_argument("--komi", type=float, default=6.5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    if args.games <= 0 or args.max_moves <= 0:
        parser.error("--games and --max-moves must be positive")

    try:
        policy = PolicyGTPEngine(board_size=9, komi=args.komi, model_path=args.policy_model)
        if args.opponent == "random":
            factory = lambda index: RandomGTPEngine(board_size=9, komi=args.komi, seed=args.seed + index)
        else:
            from src.gtp_client import GTPClient

            settings = json.loads(args.config.read_text(encoding="utf-8"))["katago"]
            paths = (settings["binary_path"], settings["model_path"], settings["config_path"])
            factory = lambda index: GTPClient(*paths)
        result = run_benchmark(policy, factory, args.games, args.max_moves, args.komi)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f"ベンチマーク失敗: {error}", file=sys.stderr)
        return 1

    rate = "算出不可" if result.win_rate is None else f"{result.win_rate:.1%}"
    def seconds(value):
        return "算出不可" if value is None else f"{value:.3f} 秒"

    print(f"9路 Policy AI 対 {args.opponent}: {result.games} 局")
    print(f"勝 {result.wins} / 負 {result.losses} / 持碁 {result.draws} / 未決着 {result.unresolved}")
    print(f"勝率（決着局のみ、持碁は半勝）: {rate}")
    print(f"Policy AI: {seconds(result.policy_seconds_per_move)}/手 ({len(result.policy_move_times)} 手)")
    print(f"{args.opponent}: {seconds(result.opponent_seconds_per_move)}/手 ({len(result.opponent_move_times)} 手)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
