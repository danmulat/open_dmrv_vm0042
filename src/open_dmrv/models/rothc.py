"""Transparent RothC style monthly soil carbon model.

Research implementation only. Check against the official RothC implementation and independently validate before project use.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class RothCInputs:
    temperatures_c: tuple[float, ...]
    rainfall_mm: tuple[float, ...]
    pet_mm: tuple[float, ...]
    clay_percent: float
    annual_plant_c_t_ha: float
    annual_manure_c_t_ha: float
    dpm_rpm_ratio: float
    soil_cover: tuple[bool, ...]

    def __post_init__(self) -> None:
        if {len(self.temperatures_c), len(self.rainfall_mm), len(self.pet_mm), len(self.soil_cover)} != {12}:
            raise ValueError("All monthly input sequences must contain 12 values")
        if not 0 <= self.clay_percent <= 100:
            raise ValueError("Clay percent must be between 0 and 100")
        if self.dpm_rpm_ratio <= 0:
            raise ValueError("DPM to RPM ratio must be positive")


@dataclass
class RothCPools:
    dpm: float
    rpm: float
    bio: float
    hum: float
    iom: float

    @property
    def total(self) -> float:
        return self.dpm + self.rpm + self.bio + self.hum + self.iom


class RothCModel:
    decomposition_rates = {"dpm": 10.0, "rpm": 0.3, "bio": 0.66, "hum": 0.02}

    def __init__(self, initial_soc_t_c_ha: float) -> None:
        if initial_soc_t_c_ha <= 0:
            raise ValueError("Initial SOC must be positive")
        iom = 0.049 * initial_soc_t_c_ha**1.139
        active = max(initial_soc_t_c_ha - iom, 0.0)
        self.pools = RothCPools(active * 0.05, active * 0.20, active * 0.05, active * 0.70, iom)

    @staticmethod
    def temperature_modifier(temperature_c: float) -> float:
        if temperature_c <= -18.3:
            return 0.0
        return 47.9 / (1.0 + exp(106.0 / (temperature_c + 18.3)))

    @staticmethod
    def moisture_modifier(rainfall_mm: float, pet_mm: float) -> float:
        if pet_mm <= 0:
            return 1.0
        return float(np.clip(0.2 + 0.8 * rainfall_mm / pet_mm, 0.2, 1.0))

    @staticmethod
    def cover_modifier(covered: bool) -> float:
        return 0.6 if covered else 1.0

    @staticmethod
    def retained_carbon_fractions(clay_percent: float) -> tuple[float, float, float]:
        ratio = 1.67 * (1.85 + 1.60 * exp(-0.0786 * clay_percent))
        retained = 1.0 / (1.0 + ratio)
        return 0.46 * retained, 0.54 * retained, 1.0 - retained

    def step_month(self, inputs: RothCInputs, month: int) -> float:
        modifier = self.temperature_modifier(inputs.temperatures_c[month]) * self.moisture_modifier(inputs.rainfall_mm[month], inputs.pet_mm[month]) * self.cover_modifier(inputs.soil_cover[month])
        plant = inputs.annual_plant_c_t_ha / 12.0
        manure = inputs.annual_manure_c_t_ha / 12.0
        dpm_fraction = inputs.dpm_rpm_ratio / (1.0 + inputs.dpm_rpm_ratio)
        self.pools.dpm += plant * dpm_fraction + manure * 0.49
        self.pools.rpm += plant * (1.0 - dpm_fraction) + manure * 0.49
        self.pools.hum += manure * 0.02
        to_bio, to_hum, to_co2 = self.retained_carbon_fractions(inputs.clay_percent)
        released = 0.0
        for pool_name in ("dpm", "rpm", "bio", "hum"):
            pool = getattr(self.pools, pool_name)
            decomposed = pool * (1.0 - exp(-self.decomposition_rates[pool_name] * modifier / 12.0))
            setattr(self.pools, pool_name, pool - decomposed)
            self.pools.bio += decomposed * to_bio
            self.pools.hum += decomposed * to_hum
            released += decomposed * to_co2
        return released

    def run(self, inputs: RothCInputs, years: int) -> list[float]:
        trajectory = [self.pools.total]
        for _ in range(years):
            for month in range(12):
                self.step_month(inputs, month)
            trajectory.append(self.pools.total)
        return trajectory


def run_scenarios_from_same_initial(initial_soc_t_c_ha: float, baseline_inputs: RothCInputs, project_inputs: RothCInputs, years: int) -> tuple[list[float], list[float]]:
    return RothCModel(initial_soc_t_c_ha).run(baseline_inputs, years), RothCModel(initial_soc_t_c_ha).run(project_inputs, years)


def mean_monthly(values: Iterable[float]) -> tuple[float, ...]:
    array = np.asarray(tuple(values), dtype=float)
    if array.size != 12:
        raise ValueError("Expected 12 monthly values")
    return tuple(float(value) for value in array)
