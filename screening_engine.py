from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================
# STATUS TYPES
# ============================================================

class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    DATA_INSUFFICIENT = "DATA INSUFFICIENT"
    NOT_EVALUATED = "NOT EVALUATED"


class CandidateStatus(str, Enum):
    SURVIVOR = "SURVIVOR"
    NEAR_MISS = "NEAR MISS"
    FAIL = "FAIL"
    DATA_INSUFFICIENT = "DATA INSUFFICIENT"
    NOT_EVALUATED = "NOT EVALUATED"


# ============================================================
# GENERIC GATE RESULT
# ============================================================

@dataclass
class GateResult:
    gate: int
    status: GateStatus
    reason: str
    metrics: dict = field(default_factory=dict)
    evidence: list = field(default_factory=list)


# ============================================================
# GATE 1 INPUT
# ============================================================

@dataclass
class Gate1Input:
    valuation_method_1: Optional[str] = None
    valuation_result_1: Optional[str] = None

    valuation_method_2: Optional[str] = None
    valuation_result_2: Optional[str] = None

    check_1_supports_undervaluation: Optional[bool] = None
    check_2_supports_undervaluation: Optional[bool] = None

    methods_materially_contradict: Optional[bool] = None

    evidence: list = field(default_factory=list)
    retrieval_attempts: list = field(default_factory=list)


# ============================================================
# GATE 2 INPUT
# ============================================================

@dataclass
class Gate2Input:
    mispricing_mechanism: Optional[str] = None
    economic_explanation: Optional[str] = None
    mechanism_supported: Optional[bool] = None

    evidence: list = field(default_factory=list)
    retrieval_attempts: list = field(default_factory=list)


# ============================================================
# GATE 3 INPUT
# ============================================================

@dataclass
class Gate3Input:
    strongest_bear_case: Optional[str] = None

    structural_impairment_sufficient: Optional[bool] = None

    unresolved_structural_risks: list = field(default_factory=list)

    evidence: list = field(default_factory=list)
    retrieval_attempts: list = field(default_factory=list)


# ============================================================
# GATE 4 INPUT
# ============================================================

@dataclass
class Gate4Input:
    catalyst: Optional[str] = None
    economic_link: Optional[str] = None
    timing_months: Optional[float] = None

    catalyst_supported: Optional[bool] = None

    evidence: list = field(default_factory=list)
    retrieval_attempts: list = field(default_factory=list)


# ============================================================
# GATE 5 INPUT
# ============================================================

@dataclass
class Gate5Input:
    current_price: Optional[float] = None

    base_operating_assumption: Optional[str] = None

    fair_value_low: Optional[float] = None
    fair_value_high: Optional[float] = None
    conservative_fair_value: Optional[float] = None
    fair_value_basis: Optional[str] = None

    adverse_operating_assumption: Optional[str] = None

    downside_low: Optional[float] = None
    downside_high: Optional[float] = None
    conservative_downside: Optional[float] = None
    downside_basis: Optional[str] = None

    months_to_value: Optional[float] = None

    evidence: list = field(default_factory=list)


# ============================================================
# BASIC MATH
# ============================================================

def annualized_return(
    current_price: float,
    fair_value: float,
    months_to_value: float,
) -> Optional[float]:

    if (
        current_price is None
        or fair_value is None
        or months_to_value is None
        or current_price <= 0
        or fair_value <= 0
        or months_to_value <= 0
    ):
        return None

    return (
        (fair_value / current_price)
        ** (12 / months_to_value)
        - 1
    )


def upside_percent(
    current_price: float,
    fair_value: float,
) -> Optional[float]:

    if (
        current_price is None
        or fair_value is None
        or current_price <= 0
    ):
        return None

    return (
        fair_value - current_price
    ) / current_price


def downside_percent(
    current_price: float,
    downside_value: float,
) -> Optional[float]:

    if (
        current_price is None
        or downside_value is None
        or current_price <= 0
    ):
        return None

    return (
        current_price - downside_value
    ) / current_price


def reward_downside_ratio(
    current_price: float,
    fair_value: float,
    downside_value: float,
) -> Optional[float]:

    if (
        current_price is None
        or fair_value is None
        or downside_value is None
    ):
        return None

    reward = fair_value - current_price
    downside = current_price - downside_value

    if downside <= 0:
        return None

    return reward / downside


# ============================================================
# GATE 1
# IS IT ACTUALLY CHEAP?
# ============================================================

def evaluate_gate_1(data: Gate1Input) -> GateResult:

    required = [
        data.valuation_method_1,
        data.valuation_result_1,
        data.valuation_method_2,
        data.valuation_result_2,
        data.check_1_supports_undervaluation,
        data.check_2_supports_undervaluation,
        data.methods_materially_contradict,
    ]

    if any(value is None for value in required):

        return GateResult(
            gate=1,
            status=GateStatus.DATA_INSUFFICIENT,
            reason=(
                "Two reliable valuation checks could not "
                "be completed."
            ),
            evidence=data.evidence,
            metrics={
                "retrieval_attempts":
                    data.retrieval_attempts
            },
        )

    if data.methods_materially_contradict:

        return GateResult(
            gate=1,
            status=GateStatus.FAIL,
            reason=(
                "The two valuation methods materially "
                "contradict the undervaluation thesis."
            ),
            evidence=data.evidence,
        )

    if not (
        data.check_1_supports_undervaluation
        and data.check_2_supports_undervaluation
    ):

        return GateResult(
            gate=1,
            status=GateStatus.FAIL,
            reason=(
                "Available valuation evidence does not "
                "establish sufficient undervaluation."
            ),
            evidence=data.evidence,
        )

    return GateResult(
        gate=1,
        status=GateStatus.PASS,
        reason=(
            "Two appropriate valuation checks support "
            "the undervaluation thesis without material "
            "contradiction."
        ),
        evidence=data.evidence,
        metrics={
            "valuation_method_1":
                data.valuation_method_1,
            "valuation_result_1":
                data.valuation_result_1,
            "valuation_method_2":
                data.valuation_method_2,
            "valuation_result_2":
                data.valuation_result_2,
        },
    )


# ============================================================
# GATE 2
# WHY IS THE MARKET WRONG?
# ============================================================

def evaluate_gate_2(data: Gate2Input) -> GateResult:

    if (
        not data.mispricing_mechanism
        or not data.economic_explanation
        or data.mechanism_supported is None
    ):

        return GateResult(
            gate=2,
            status=GateStatus.DATA_INSUFFICIENT,
            reason=(
                "A concrete, evidence-supported "
                "mispricing mechanism could not be "
                "reliably evaluated."
            ),
            evidence=data.evidence,
            metrics={
                "retrieval_attempts":
                    data.retrieval_attempts
            },
        )

    if not data.mechanism_supported:

        return GateResult(
            gate=2,
            status=GateStatus.FAIL,
            reason=(
                "Current evidence does not support a "
                "specific economic or market mechanism "
                "explaining why the price may be wrong."
            ),
            evidence=data.evidence,
        )

    return GateResult(
        gate=2,
        status=GateStatus.PASS,
        reason=(
            "A concrete, evidence-supported mechanism "
            "exists that could explain the apparent "
            "mispricing."
        ),
        evidence=data.evidence,
        metrics={
            "mispricing_mechanism":
                data.mispricing_mechanism,
            "economic_explanation":
                data.economic_explanation,
        },
    )


# ============================================================
# GATE 3
# WHY MIGHT THE MARKET BE RIGHT?
# ============================================================

def evaluate_gate_3(data: Gate3Input) -> GateResult:

    if (
        not data.strongest_bear_case
        or data.structural_impairment_sufficient
        is None
    ):

        return GateResult(
            gate=3,
            status=GateStatus.DATA_INSUFFICIENT,
            reason=(
                "The strongest structural bear case "
                "could not be reliably evaluated."
            ),
            evidence=data.evidence,
            metrics={
                "retrieval_attempts":
                    data.retrieval_attempts
            },
        )

    if data.structural_impairment_sufficient:

        return GateResult(
            gate=3,
            status=GateStatus.FAIL,
            reason=(
                "Structural deterioration provides a "
                "sufficient explanation for the apparent "
                "valuation discount."
            ),
            evidence=data.evidence,
            metrics={
                "strongest_bear_case":
                    data.strongest_bear_case
            },
        )

    return GateResult(
        gate=3,
        status=GateStatus.PASS,
        reason=(
            "The bear case remains relevant, but current "
            "evidence does not establish structural "
            "impairment as a sufficient explanation for "
            "the discount."
        ),
        evidence=data.evidence,
        metrics={
            "strongest_bear_case":
                data.strongest_bear_case,
            "unresolved_structural_risks":
                data.unresolved_structural_risks,
        },
    )


# ============================================================
# GATE 4
# WHAT CHANGES THE MARKET'S MIND?
# ============================================================

def evaluate_gate_4(data: Gate4Input) -> GateResult:

    if (
        not data.catalyst
        or not data.economic_link
        or data.timing_months is None
        or data.catalyst_supported is None
    ):

        return GateResult(
            gate=4,
            status=GateStatus.DATA_INSUFFICIENT,
            reason=(
                "A specific evidence-supported catalyst "
                "with economic impact and timing could "
                "not be reliably established."
            ),
            evidence=data.evidence,
            metrics={
                "retrieval_attempts":
                    data.retrieval_attempts
            },
        )

    timing_valid = (
        6 <= data.timing_months <= 18
    )

    if (
        not data.catalyst_supported
        or not timing_valid
    ):

        return GateResult(
            gate=4,
            status=GateStatus.FAIL,
            reason=(
                "No sufficiently supported catalyst or "
                "operating mechanism is expected to "
                "affect value within approximately "
                "6–18 months."
            ),
            evidence=data.evidence,
        )

    return GateResult(
        gate=4,
        status=GateStatus.PASS,
        reason=(
            "A specific evidence-supported catalyst "
            "exists with a plausible economic impact "
            "within the required time horizon."
        ),
        evidence=data.evidence,
        metrics={
            "catalyst":
                data.catalyst,
            "economic_link":
                data.economic_link,
            "timing_months":
                data.timing_months,
        },
    )


# ============================================================
# GATE 5
# IS THE PAYOFF WORTH IT?
# ============================================================

def evaluate_gate_5(
    data: Gate5Input,
    minimum_annualized_return: float = 0.15,
    minimum_reward_downside: float = 2.0,
) -> GateResult:

    required = [
        data.current_price,
        data.base_operating_assumption,
        data.fair_value_low,
        data.fair_value_high,
        data.conservative_fair_value,
        data.fair_value_basis,
        data.adverse_operating_assumption,
        data.downside_low,
        data.downside_high,
        data.conservative_downside,
        data.downside_basis,
        data.months_to_value,
    ]

    if any(value is None for value in required):

        return GateResult(
            gate=5,
            status=GateStatus.DATA_INSUFFICIENT,
            reason=(
                "Required valuation or operating "
                "scenario inputs are unavailable."
            ),
            evidence=data.evidence,
        )

    # Conservative fair value must not exceed
    # the high end of the stated fair-value range.

    if not (
        min(
            data.fair_value_low,
            data.fair_value_high,
        )
        <= data.conservative_fair_value
        <= max(
            data.fair_value_low,
            data.fair_value_high,
        )
    ):

        return GateResult(
            gate=5,
            status=GateStatus.DATA_INSUFFICIENT,
            reason=(
                "Conservative fair value is outside "
                "the stated reasonable fair-value range."
            ),
            evidence=data.evidence,
        )

    # Downside must likewise fall inside
    # its stated reasonable range.

    if not (
        min(
            data.downside_low,
            data.downside_high,
        )
        <= data.conservative_downside
        <= max(
            data.downside_low,
            data.downside_high,
        )
    ):

        return GateResult(
            gate=5,
            status=GateStatus.DATA_INSUFFICIENT,
            reason=(
                "Conservative downside value is outside "
                "the stated reasonable downside range."
            ),
            evidence=data.evidence,
        )

    ann_return = annualized_return(
        current_price=data.current_price,
        fair_value=data.conservative_fair_value,
        months_to_value=data.months_to_value,
    )

    upside = upside_percent(
        current_price=data.current_price,
        fair_value=data.conservative_fair_value,
    )

    downside = downside_percent(
        current_price=data.current_price,
        downside_value=data.conservative_downside,
    )

    reward_downside = reward_downside_ratio(
        current_price=data.current_price,
        fair_value=data.conservative_fair_value,
        downside_value=data.conservative_downside,
    )

    metrics = {
        "current_price":
            data.current_price,

        "base_operating_assumption":
            data.base_operating_assumption,

        "fair_value_range": (
            data.fair_value_low,
            data.fair_value_high,
        ),

        "conservative_fair_value":
            data.conservative_fair_value,

        "fair_value_basis":
            data.fair_value_basis,

        "adverse_operating_assumption":
            data.adverse_operating_assumption,

        "downside_range": (
            data.downside_low,
            data.downside_high,
        ),

        "conservative_downside":
            data.conservative_downside,

        "downside_basis":
            data.downside_basis,

        "upside_percent":
            upside,

        "downside_percent":
            downside,

        "reward_downside":
            reward_downside,

        "annualized_return":
            ann_return,

        "months_to_value":
            data.months_to_value,

        "minimum_annualized_return":
            minimum_annualized_return,

        "minimum_reward_downside":
            minimum_reward_downside,
    }

    if (
        ann_return is None
        or reward_downside is None
    ):

        return GateResult(
            gate=5,
            status=GateStatus.DATA_INSUFFICIENT,
            reason=(
                "Gate 5 return or downside metrics "
                "could not be calculated reliably."
            ),
            metrics=metrics,
            evidence=data.evidence,
        )

    return_pass = (
        ann_return
        >= minimum_annualized_return
    )

    asymmetry_pass = (
        reward_downside
        >= minimum_reward_downside
    )

    if return_pass and asymmetry_pass:

        return GateResult(
            gate=5,
            status=GateStatus.PASS,
            reason=(
                f"Using the conservative fair value "
                f"and conservative downside case, "
                f"annualized base return is "
                f"{ann_return:.1%} and reward/downside "
                f"is {reward_downside:.2f}x."
            ),
            metrics=metrics,
            evidence=data.evidence,
        )

    failure_reasons = []

    if not return_pass:

        failure_reasons.append(
            f"annualized base return "
            f"{ann_return:.1%} is below "
            f"{minimum_annualized_return:.0%}"
        )

    if not asymmetry_pass:

        failure_reasons.append(
            f"reward/downside "
            f"{reward_downside:.2f}x is below "
            f"{minimum_reward_downside:.2f}x"
        )

    return GateResult(
        gate=5,
        status=GateStatus.FAIL,
        reason=(
            "Fails the robustness rule using "
            "conservative valuation assumptions: "
            + "; ".join(failure_reasons)
        ),
        metrics=metrics,
        evidence=data.evidence,
    )


# ============================================================
# FIRST FAILED GATE
# ============================================================

def first_failed_gate(
    gates: dict,
) -> Optional[int]:

    for gate_number in range(1, 6):

        result = gates.get(gate_number)

        if (
            result
            and result.status == GateStatus.FAIL
        ):
            return gate_number

    return None


# ============================================================
# FINAL CLASSIFICATION
# ============================================================

def classify_candidate(
    gates: dict,
) -> CandidateStatus:

    for gate_number in range(1, 6):

        result = gates.get(gate_number)

        if result is None:

            return CandidateStatus.NOT_EVALUATED

        if (
            result.status
            == GateStatus.DATA_INSUFFICIENT
        ):

            return (
                CandidateStatus
                .DATA_INSUFFICIENT
            )

        if result.status == GateStatus.FAIL:

            if gate_number == 5:

                return (
                    CandidateStatus
                    .NEAR_MISS
                )

            return CandidateStatus.FAIL

        if (
            result.status
            != GateStatus.PASS
        ):

            return (
                CandidateStatus
                .NOT_EVALUATED
            )

    return CandidateStatus.SURVIVOR


# ============================================================
# STOP-AFTER-FIRST-FAILURE RULE
# ============================================================

def should_continue_after(
    gate_result: GateResult,
) -> bool:

    return (
        gate_result.status
        == GateStatus.PASS
    )


# ============================================================
# GATE 5 NEAR-MISS RECHECK PRICE
# ============================================================

def gate_5_recheck_price(
    fair_value: float,
    downside_value: float,
    months_to_value: float,
    minimum_annualized_return: float = 0.15,
    minimum_reward_downside: float = 2.0,
) -> Optional[dict]:

    if (
        fair_value is None
        or downside_value is None
        or months_to_value is None
        or fair_value <= 0
        or downside_value < 0
        or months_to_value <= 0
    ):
        return None

    # Maximum price that satisfies
    # the annualized-return hurdle.

    return_price_limit = (
        fair_value
        /
        (
            1
            + minimum_annualized_return
        )
        ** (
            months_to_value / 12
        )
    )

    # Solve:
    #
    # (FV - P) / (P - D) >= R
    #
    # For R = required reward/downside.
    #
    # P <= (FV + R*D) / (1 + R)

    asymmetry_price_limit = (
        fair_value
        + minimum_reward_downside
        * downside_value
    ) / (
        1
        + minimum_reward_downside
    )

    qualifying_price = min(
        return_price_limit,
        asymmetry_price_limit,
    )

    binding_constraint = (
        "annualized return"
        if return_price_limit
        <= asymmetry_price_limit
        else "reward/downside"
    )

    return {
        "return_hurdle_price":
            return_price_limit,

        "reward_downside_hurdle_price":
            asymmetry_price_limit,

        "qualifying_price":
            qualifying_price,

        "binding_constraint":
            binding_constraint,
    }
