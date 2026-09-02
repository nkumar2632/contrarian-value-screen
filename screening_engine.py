from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ============================================================
# GATE STATUS
# ============================================================

class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    DATA_INSUFFICIENT = "DATA INSUFFICIENT"
    NOT_EVALUATED = "NOT EVALUATED"


# ============================================================
# GATE RESULT
# ============================================================

@dataclass
class GateResult:
    gate: int
    status: GateStatus
    reason: str
    metrics: Optional[dict] = None


# ============================================================
# BASIC VALUATION MATH
# ============================================================

def annualized_return(
    current_price: float,
    fair_value: float,
    months_to_value: float,
) -> Optional[float]:
    """
    Calculate annualized return from current price to fair value.

    Returns decimal form:
    0.15 = 15%
    """

    if (
        current_price is None
        or fair_value is None
        or months_to_value is None
        or current_price <= 0
        or fair_value <= 0
        or months_to_value <= 0
    ):
        return None

    return (fair_value / current_price) ** (12 / months_to_value) - 1


def reward_downside_ratio(
    current_price: float,
    fair_value: float,
    downside_value: float,
) -> Optional[float]:
    """
    Reward = fair value - current price
    Downside = current price - downside value

    Reward/downside must be positive and meaningful.
    """

    if (
        current_price is None
        or fair_value is None
        or downside_value is None
    ):
        return None

    upside = fair_value - current_price
    downside = current_price - downside_value

    if downside <= 0:
        return None

    return upside / downside


# ============================================================
# GATE 5 — RETURN / ASYMMETRY
# ============================================================

def evaluate_gate_5(
    current_price: float,
    fair_value: float,
    downside_value: float,
    months_to_value: float,
    minimum_annualized_return: float = 0.15,
    minimum_reward_downside: float = 2.0,
) -> GateResult:
    """
    Gate 5 requires BOTH:

    1. Base-case annualized return >= 15%
    2. Reward/downside >= 2.0x

    Missing required inputs produce DATA INSUFFICIENT,
    not FAIL.
    """

    ann_return = annualized_return(
        current_price,
        fair_value,
        months_to_value,
    )

    reward_downside = reward_downside_ratio(
        current_price,
        fair_value,
        downside_value,
    )

    metrics = {
        "current_price": current_price,
        "fair_value": fair_value,
        "downside_value": downside_value,
        "months_to_value": months_to_value,
        "annualized_return": ann_return,
        "reward_downside": reward_downside,
        "minimum_annualized_return": minimum_annualized_return,
        "minimum_reward_downside": minimum_reward_downside,
    }

    if ann_return is None or reward_downside is None:
        return GateResult(
            gate=5,
            status=GateStatus.DATA_INSUFFICIENT,
            reason="Required valuation inputs are missing or invalid.",
            metrics=metrics,
        )

    annualized_pass = ann_return >= minimum_annualized_return
    asymmetry_pass = reward_downside >= minimum_reward_downside

    if annualized_pass and asymmetry_pass:
        return GateResult(
            gate=5,
            status=GateStatus.PASS,
            reason=(
                f"Annualized return {ann_return:.1%} and "
                f"reward/downside {reward_downside:.2f}x "
                "meet Gate 5 requirements."
            ),
            metrics=metrics,
        )

    failure_reasons = []

    if not annualized_pass:
        failure_reasons.append(
            f"annualized return {ann_return:.1%} is below "
            f"{minimum_annualized_return:.0%}"
        )

    if not asymmetry_pass:
        failure_reasons.append(
            f"reward/downside {reward_downside:.2f}x is below "
            f"{minimum_reward_downside:.2f}x"
        )

    return GateResult(
        gate=5,
        status=GateStatus.FAIL,
        reason="; ".join(failure_reasons),
        metrics=metrics,
    )


# ============================================================
# FINAL CLASSIFICATION
# ============================================================

def classify_candidate(gates: dict) -> str:
    """
    Determine the candidate's overall status.

    SURVIVOR:
        All five gates PASS.

    NEAR MISS:
        Gates 1–4 PASS and Gate 5 FAIL.

    DATA INSUFFICIENT:
        At least one evaluated gate lacks required data and
        no earlier gate has already failed.

    FAIL:
        Any of Gates 1–4 FAIL.
    """

    for gate_number in range(1, 5):
        gate = gates.get(gate_number)

        if gate is None:
            return "DATA INSUFFICIENT"

        if gate.status == GateStatus.FAIL:
            return "FAIL"

        if gate.status == GateStatus.DATA_INSUFFICIENT:
            return "DATA INSUFFICIENT"

        if gate.status != GateStatus.PASS:
            return "DATA INSUFFICIENT"

    gate_5 = gates.get(5)

    if gate_5 is None:
        return "DATA INSUFFICIENT"

    if gate_5.status == GateStatus.DATA_INSUFFICIENT:
        return "DATA INSUFFICIENT"

    if gate_5.status == GateStatus.FAIL:
        return "NEAR MISS"

    if gate_5.status == GateStatus.PASS:
        return "SURVIVOR"

    return "DATA INSUFFICIENT"
