"""AIの着手評価とSGFへ保存する着手履歴を表す。"""

from dataclasses import dataclass

from .rules import Point


@dataclass(frozen=True)
class TacticalMove:
    """Policy順位とは別に評価する取り・救出候補。"""

    move: Point
    captured_stones: int
    rescued_stones: int


@dataclass(frozen=True)
class MoveRisk:
    """候補着手後に相手の次の一手で生じる石の損失リスク。"""

    self_atari_stones: int
    immediate_loss_stones: int
    penalty: float


@dataclass(frozen=True)
class CandidateEvaluation:
    """PolicyValue AIが評価した一つの候補手。"""

    move: Point | None
    policy_probability: float
    value: float
    combined_score: float
    captured_stones: int = 0
    rescued_stones: int = 0
    rescue_priority: float = 0.0
    self_atari_stones: int = 0
    immediate_loss_stones: int = 0
    risk_penalty: float = 0.0


@dataclass(frozen=True)
class MoveAnalysis:
    """一回のAI推論結果。"""

    selected_move: Point | None
    policy_weight: float
    value_weight: float
    candidates: tuple[CandidateEvaluation, ...]


@dataclass(frozen=True)
class MoveRecord:
    """対局中の一手と、その手に対応する任意のAI診断情報。"""

    color: int
    move: Point | None
    analysis: MoveAnalysis | None = None
