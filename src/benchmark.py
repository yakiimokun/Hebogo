"""9路の GTP 対局結果と着手時間を集計する。"""

from dataclasses import dataclass
from statistics import mean

from .gtp_match import GTPMatch


@dataclass(frozen=True)
class BenchmarkResult:
    games: int
    wins: int
    losses: int
    draws: int
    unresolved: int
    policy_move_times: tuple[float, ...]
    opponent_move_times: tuple[float, ...]

    @property
    def win_rate(self):
        """決着した局を分母とし、持碁を半勝として数える。"""
        decided = self.wins + self.losses + self.draws
        return (self.wins + self.draws / 2) / decided if decided else None

    @property
    def policy_seconds_per_move(self):
        return mean(self.policy_move_times) if self.policy_move_times else None

    @property
    def opponent_seconds_per_move(self):
        return mean(self.opponent_move_times) if self.opponent_move_times else None


def _winner(result):
    if result.reason == "black_resigned":
        return "white"
    if result.reason == "white_resigned":
        return "black"
    if result.reason != "two_passes" or result.final_score is None:
        return None
    score = result.final_score.strip().upper()
    if score == "0" or score in ("DRAW", "JIGO"):
        return "draw"
    if score.startswith("B+"):
        return "black"
    if score.startswith("W+"):
        return "white"
    raise ValueError(f"unrecognized final_score: {result.final_score!r}")


def run_benchmark(policy, opponent_factory, games=10, max_moves=243, komi=6.5):
    """各局で黒白を交代し、Policy AI 視点の結果を返す。"""
    if games <= 0 or max_moves <= 0:
        raise ValueError("games and max_moves must be positive")
    wins = losses = draws = unresolved = 0
    policy_times = []
    opponent_times = []
    for game_index in range(games):
        opponent = opponent_factory(game_index)
        policy_color = "black" if game_index % 2 == 0 else "white"
        black, white = (policy, opponent) if policy_color == "black" else (opponent, policy)
        try:
            result = GTPMatch(black, white, board_size=9, komi=komi).play(max_moves=max_moves)
            winner = _winner(result)
            if winner is None:
                unresolved += 1
            elif winner == "draw":
                draws += 1
            elif winner == policy_color:
                wins += 1
            else:
                losses += 1
            for color, seconds in result.move_times:
                (policy_times if color == policy_color else opponent_times).append(seconds)
        finally:
            close = getattr(opponent, "close", None)
            if close is not None:
                close()
    return BenchmarkResult(
        games, wins, losses, draws, unresolved,
        tuple(policy_times), tuple(opponent_times),
    )
