"""AIの着手評価とSGFへ保存する着手履歴を表す。"""

from dataclasses import dataclass

from .rules import Point


@dataclass(frozen=True)
class CandidateEvaluation:
    """PolicyValue AIが評価した一つの候補手。"""

    move: Point | None
    policy_probability: float
    value: float
    combined_score: float


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
