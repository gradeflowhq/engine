from ..result import Result
from ..types import CompletenessAggregation


def output_fn(passed_list: list[bool], mode: CompletenessAggregation) -> float:
    if mode == "ALL":
        return float(all(passed_list))
    elif mode == "ANY":
        return float(any(passed_list))
    elif mode == "PARTIAL":
        return sum(passed_list) / len(passed_list)
    else:
        raise ValueError(f"Unsupported aggregation mode: {mode}")


def passed_fn(passed_list: list[bool], mode: CompletenessAggregation) -> bool:
    if mode == "ALL":
        return all(passed_list)
    elif mode in {"ANY", "PARTIAL"}:
        return any(passed_list)
    else:
        raise ValueError(f"Unsupported aggregation mode: {mode}")


def points_fn(result: Result, mode: CompletenessAggregation, max_points: float) -> float:
    if not isinstance(result.output, float):
        raise ValueError("Result output must be a float for points calculation.")
    if mode in {"ALL", "ANY", "CONTAIN", "NOT_CONTAIN"}:
        return max_points if result.passed else 0.0
    elif mode == "PARTIAL":
        return max_points * result.output
    else:
        raise ValueError(f"Unsupported aggregation mode: {mode}")
