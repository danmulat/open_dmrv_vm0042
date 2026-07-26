"""Illustrative uncertainty utilities for software testing only."""

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class UncertaintyResult:
    estimate: float
    standard_error: float
    relative_uncertainty_percent: float
    deduction_percent: float
    conservative_value: float


def combine_standard_errors(*standard_errors: float) -> float:
    return sqrt(sum(value**2 for value in standard_errors))


def illustrative_uncertainty_deduction(estimate: float, standard_error: float, threshold_percent: float = 15.0) -> UncertaintyResult:
    relative = 0.0 if estimate == 0 else abs(standard_error / estimate) * 100.0
    deduction = max(0.0, relative - threshold_percent)
    conservative = estimate - max(0.0, estimate * deduction / 100.0)
    return UncertaintyResult(estimate, standard_error, relative, deduction, conservative)
