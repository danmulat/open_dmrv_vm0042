"""RothC carbon turnover model adapted from Rothamsted Research RothC_Py.

This file contains modified code derived from RothC_Py:
https://github.com/Rothamsted-Models/RothC_Py

Original work copyright 2024 Rothamsted Research and licensed under the
Apache License, Version 2.0. Modifications copyright 2026 Daniel Mulat.

The implementation preserves the official monthly carbon turnover equations,
pool structure, temperature modifier, soil moisture deficit calculation,
plant cover modifier, decomposition constants, clay dependent partitioning,
plant input partitioning, and farmyard manure partitioning.

Radiocarbon calculations from RothC_Py are not included because the open dMRV
accounting workflow currently requires carbon stocks and stock changes only.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable, Sequence

import numpy as np

MONTHS_PER_YEAR = 12
DECOMPOSITION_RATES = {
    "dpm": 10.0,
    "rpm": 0.3,
    "bio": 0.66,
    "hum": 0.02,
}


def _as_monthly(
    values: Sequence[float] | None,
    annual_total: float,
) -> tuple[float, ...]:
    if values is not None:
        result = tuple(float(value) for value in values)
        if len(result) != MONTHS_PER_YEAR:
            raise ValueError("Monthly input sequences must contain 12 values")
        return result
    return (float(annual_total) / MONTHS_PER_YEAR,) * MONTHS_PER_YEAR


@dataclass(frozen=True)
class RothCInputs:
    """Monthly climate, management, and carbon inputs for one repeating year.

    ``pet_mm`` is interpreted as monthly open pan evaporation to match the
    RothC_Py input variable ``Evap``. For exact official model reproduction,
    supply measured or derived open pan evaporation rather than reference
    evapotranspiration.

    Annual carbon inputs are distributed equally across months unless explicit
    monthly sequences are supplied.
    """

    temperatures_c: tuple[float, ...]
    rainfall_mm: tuple[float, ...]
    pet_mm: tuple[float, ...]
    clay_percent: float
    annual_plant_c_t_ha: float
    annual_manure_c_t_ha: float
    dpm_rpm_ratio: float
    soil_cover: tuple[bool, ...]
    depth_cm: float = 30.0
    monthly_plant_c_t_ha: tuple[float, ...] | None = None
    monthly_manure_c_t_ha: tuple[float, ...] | None = None
    monthly_dpm_rpm_ratio: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        monthly = (
            self.temperatures_c,
            self.rainfall_mm,
            self.pet_mm,
            self.soil_cover,
        )
        if any(len(values) != MONTHS_PER_YEAR for values in monthly):
            raise ValueError("All climate and cover sequences must contain 12 values")
        if not 0.0 <= self.clay_percent <= 100.0:
            raise ValueError("Clay percent must be between 0 and 100")
        if self.depth_cm <= 0.0:
            raise ValueError("Soil depth must be positive")
        if self.annual_plant_c_t_ha < 0.0 or self.annual_manure_c_t_ha < 0.0:
            raise ValueError("Carbon inputs cannot be negative")
        if self.dpm_rpm_ratio <= 0.0:
            raise ValueError("DPM to RPM ratio must be positive")
        _as_monthly(self.monthly_plant_c_t_ha, self.annual_plant_c_t_ha)
        _as_monthly(self.monthly_manure_c_t_ha, self.annual_manure_c_t_ha)
        ratios = self.dpm_rpm_ratios
        if any(value <= 0.0 for value in ratios):
            raise ValueError("All monthly DPM to RPM ratios must be positive")

    @property
    def plant_c_inputs(self) -> tuple[float, ...]:
        return _as_monthly(
            self.monthly_plant_c_t_ha,
            self.annual_plant_c_t_ha,
        )

    @property
    def manure_c_inputs(self) -> tuple[float, ...]:
        return _as_monthly(
            self.monthly_manure_c_t_ha,
            self.annual_manure_c_t_ha,
        )

    @property
    def dpm_rpm_ratios(self) -> tuple[float, ...]:
        if self.monthly_dpm_rpm_ratio is None:
            return (float(self.dpm_rpm_ratio),) * MONTHS_PER_YEAR
        values = tuple(float(value) for value in self.monthly_dpm_rpm_ratio)
        if len(values) != MONTHS_PER_YEAR:
            raise ValueError("Monthly DPM to RPM ratios must contain 12 values")
        return values


@dataclass
class RothCPools:
    """RothC carbon pools in tonnes C per hectare."""

    dpm: float = 0.0
    rpm: float = 0.0
    bio: float = 0.0
    hum: float = 0.0
    iom: float = 0.0

    def __post_init__(self) -> None:
        if any(value < 0.0 for value in self.as_tuple()):
            raise ValueError("RothC pools cannot be negative")

    @property
    def total(self) -> float:
        return self.dpm + self.rpm + self.bio + self.hum + self.iom

    @property
    def active_total(self) -> float:
        return self.dpm + self.rpm + self.bio + self.hum

    def as_tuple(self) -> tuple[float, float, float, float, float]:
        return self.dpm, self.rpm, self.bio, self.hum, self.iom

    def copy(self) -> "RothCPools":
        return RothCPools(*self.as_tuple())


@dataclass(frozen=True)
class RothCMonthlyResult:
    year: int
    month: int
    dpm_t_c_ha: float
    rpm_t_c_ha: float
    bio_t_c_ha: float
    hum_t_c_ha: float
    iom_t_c_ha: float
    soc_t_c_ha: float
    soil_water_deficit_mm: float
    temperature_modifier: float
    moisture_modifier: float
    cover_modifier: float
    co2_loss_t_c_ha: float


class RothCModel:
    """Official RothC_Py carbon equations with a reusable object interface."""

    decomposition_rates = DECOMPOSITION_RATES

    def __init__(
        self,
        initial_soc_t_c_ha: float | None = None,
        *,
        clay_percent: float = 30.0,
        depth_cm: float = 30.0,
        pools: RothCPools | None = None,
    ) -> None:
        if not 0.0 <= clay_percent <= 100.0:
            raise ValueError("Clay percent must be between 0 and 100")
        if depth_cm <= 0.0:
            raise ValueError("Soil depth must be positive")
        if pools is not None and initial_soc_t_c_ha is not None:
            raise ValueError("Supply either initial SOC or explicit pools, not both")

        self.clay_percent = float(clay_percent)
        self.depth_cm = float(depth_cm)
        self.soil_water_deficit_mm = 0.0

        if pools is not None:
            self.pools = pools.copy()
        elif initial_soc_t_c_ha is not None:
            self.pools = self.pools_from_measured_soc(initial_soc_t_c_ha)
        else:
            self.pools = RothCPools()

    @staticmethod
    def inert_organic_matter(initial_soc_t_c_ha: float) -> float:
        """Estimate inert organic matter using the Falloon relationship."""

        if initial_soc_t_c_ha <= 0.0:
            raise ValueError("Initial SOC must be positive")
        return 0.049 * initial_soc_t_c_ha**1.139

    @classmethod
    def pools_from_measured_soc(cls, initial_soc_t_c_ha: float) -> RothCPools:
        """Create pools that sum exactly to measured initial SOC.

        The active pool fractions provide a deterministic initialization for
        scenario comparison. For project application, prefer equilibrium
        initialization with calibrated historical carbon inputs, followed by
        scaling or inverse estimation against measured initial SOC.
        """

        iom = min(cls.inert_organic_matter(initial_soc_t_c_ha), initial_soc_t_c_ha)
        active = initial_soc_t_c_ha - iom
        return RothCPools(
            dpm=active * 0.05,
            rpm=active * 0.20,
            bio=active * 0.05,
            hum=active * 0.70,
            iom=iom,
        )

    @staticmethod
    def temperature_modifier(temperature_c: float) -> float:
        """Official RothC_Py temperature rate modifier."""

        if temperature_c < -5.0:
            return 0.0
        return 47.91 / (exp(106.06 / (temperature_c + 18.27)) + 1.0)

    @staticmethod
    def cover_modifier(covered: bool) -> float:
        """Official RothC_Py plant retention modifier."""

        return 0.6 if covered else 1.0

    def moisture_modifier(
        self,
        rainfall_mm: float,
        open_pan_evaporation_mm: float,
        covered: bool,
    ) -> float:
        """Official RothC_Py soil moisture deficit calculation."""

        smd_max = -(20.0 + 1.3 * self.clay_percent - 0.01 * self.clay_percent**2)
        smd_max_adjusted = smd_max * self.depth_cm / 23.0
        smd_one_bar = 0.444 * smd_max_adjusted
        smd_bare = 0.556 * smd_max_adjusted
        deficit_change = rainfall_mm - 0.75 * open_pan_evaporation_mm

        minimum_deficit = min(0.0, self.soil_water_deficit_mm + deficit_change)
        minimum_bare = min(smd_bare, self.soil_water_deficit_mm)

        if covered:
            self.soil_water_deficit_mm = max(smd_max_adjusted, minimum_deficit)
        else:
            self.soil_water_deficit_mm = max(minimum_bare, minimum_deficit)

        if self.soil_water_deficit_mm > smd_one_bar:
            return 1.0

        return 0.2 + (
            0.8
            * (smd_max_adjusted - self.soil_water_deficit_mm)
            / (smd_max_adjusted - smd_one_bar)
        )

    def _decompose(self, rate_modifier: float) -> float:
        original = {
            "dpm": self.pools.dpm,
            "rpm": self.pools.rpm,
            "bio": self.pools.bio,
            "hum": self.pools.hum,
        }
        decomposed = {
            name: value
            * (1.0 - exp(-rate_modifier * self.decomposition_rates[name] / 12.0))
            for name, value in original.items()
        }

        partition_ratio = 1.67 * (
            1.85 + 1.60 * exp(-0.0786 * self.clay_percent)
        )
        total_decomposed = sum(decomposed.values())
        co2_loss = total_decomposed * partition_ratio / (partition_ratio + 1.0)
        to_bio = total_decomposed * 0.46 / (partition_ratio + 1.0)
        to_hum = total_decomposed * 0.54 / (partition_ratio + 1.0)

        self.pools.dpm = original["dpm"] - decomposed["dpm"]
        self.pools.rpm = original["rpm"] - decomposed["rpm"]
        self.pools.bio = original["bio"] - decomposed["bio"] + to_bio
        self.pools.hum = original["hum"] - decomposed["hum"] + to_hum
        return co2_loss

    def step_month(
        self,
        inputs: RothCInputs,
        month: int,
        *,
        year: int = 1,
    ) -> RothCMonthlyResult:
        """Run one month using the official RothC order of operations."""

        if month not in range(MONTHS_PER_YEAR):
            raise ValueError("Month index must be between 0 and 11")
        if (
            inputs.clay_percent != self.clay_percent
            or inputs.depth_cm != self.depth_cm
        ):
            raise ValueError("Model clay and depth must match RothC inputs")

        temperature_modifier = self.temperature_modifier(
            inputs.temperatures_c[month]
        )
        moisture_modifier = self.moisture_modifier(
            inputs.rainfall_mm[month],
            inputs.pet_mm[month],
            inputs.soil_cover[month],
        )
        cover_modifier = self.cover_modifier(inputs.soil_cover[month])
        rate_modifier = (
            temperature_modifier * moisture_modifier * cover_modifier
        )
        co2_loss = self._decompose(rate_modifier)

        plant_input = inputs.plant_c_inputs[month]
        manure_input = inputs.manure_c_inputs[month]
        ratio = inputs.dpm_rpm_ratios[month]

        self.pools.dpm += ratio / (ratio + 1.0) * plant_input + 0.49 * manure_input
        self.pools.rpm += 1.0 / (ratio + 1.0) * plant_input + 0.49 * manure_input
        self.pools.hum += 0.02 * manure_input

        return RothCMonthlyResult(
            year=year,
            month=month + 1,
            dpm_t_c_ha=self.pools.dpm,
            rpm_t_c_ha=self.pools.rpm,
            bio_t_c_ha=self.pools.bio,
            hum_t_c_ha=self.pools.hum,
            iom_t_c_ha=self.pools.iom,
            soc_t_c_ha=self.pools.total,
            soil_water_deficit_mm=self.soil_water_deficit_mm,
            temperature_modifier=temperature_modifier,
            moisture_modifier=moisture_modifier,
            cover_modifier=cover_modifier,
            co2_loss_t_c_ha=co2_loss,
        )

    def run_year(
        self,
        inputs: RothCInputs,
        *,
        year: int = 1,
    ) -> list[RothCMonthlyResult]:
        return [
            self.step_month(inputs, month, year=year)
            for month in range(MONTHS_PER_YEAR)
        ]

    def run_monthly(
        self,
        inputs: RothCInputs,
        years: int,
    ) -> list[RothCMonthlyResult]:
        if years < 0:
            raise ValueError("Years cannot be negative")
        results: list[RothCMonthlyResult] = []
        for year in range(1, years + 1):
            results.extend(self.run_year(inputs, year=year))
        return results

    def run(self, inputs: RothCInputs, years: int) -> list[float]:
        """Return annual SOC trajectory while retaining the previous API."""

        trajectory = [self.pools.total]
        for year in range(1, years + 1):
            self.run_year(inputs, year=year)
            trajectory.append(self.pools.total)
        return trajectory

    def spin_up(
        self,
        inputs: RothCInputs,
        *,
        tolerance_t_c_ha: float = 1e-6,
        max_years: int = 100_000,
    ) -> int:
        """Run a repeating year until active pool change reaches tolerance."""

        if tolerance_t_c_ha <= 0.0:
            raise ValueError("Tolerance must be positive")
        previous_active = 0.0
        for year in range(1, max_years + 1):
            self.run_year(inputs, year=year)
            difference = abs(self.pools.active_total - previous_active)
            if difference <= tolerance_t_c_ha:
                return year
            previous_active = self.pools.active_total
        raise RuntimeError("RothC equilibrium spin up did not converge")

    def scale_active_pools_to_soc(self, measured_soc_t_c_ha: float) -> None:
        """Scale active pools so total SOC equals a measured starting stock."""

        if measured_soc_t_c_ha <= self.pools.iom:
            raise ValueError("Measured SOC must be greater than IOM")
        if self.pools.active_total <= 0.0:
            raise ValueError("Active pools must be initialized before scaling")
        factor = (
            measured_soc_t_c_ha - self.pools.iom
        ) / self.pools.active_total
        self.pools.dpm *= factor
        self.pools.rpm *= factor
        self.pools.bio *= factor
        self.pools.hum *= factor


def run_scenarios_from_same_initial(
    initial_soc_t_c_ha: float,
    baseline_inputs: RothCInputs,
    project_inputs: RothCInputs,
    years: int,
) -> tuple[list[float], list[float]]:
    """Run baseline and project scenarios from identical measured SOC."""

    if (
        baseline_inputs.clay_percent != project_inputs.clay_percent
        or baseline_inputs.depth_cm != project_inputs.depth_cm
    ):
        raise ValueError("Baseline and project soil properties must match")

    baseline = RothCModel(
        initial_soc_t_c_ha,
        clay_percent=baseline_inputs.clay_percent,
        depth_cm=baseline_inputs.depth_cm,
    )
    project = RothCModel(
        initial_soc_t_c_ha,
        clay_percent=project_inputs.clay_percent,
        depth_cm=project_inputs.depth_cm,
    )
    return baseline.run(baseline_inputs, years), project.run(project_inputs, years)


def mean_monthly(values: Iterable[float]) -> tuple[float, ...]:
    array = np.asarray(tuple(values), dtype=float)
    if array.size != MONTHS_PER_YEAR:
        raise ValueError("Expected 12 monthly values")
    return tuple(float(value) for value in array)
