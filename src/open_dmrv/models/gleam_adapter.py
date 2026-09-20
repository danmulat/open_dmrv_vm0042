"""Interfaces for integrating the pinned FAO GLEAM X livestock calculation chain.

This module does not substitute IPCC defaults for GLEAM X. It provides typed boundaries
for the staged port of the FAO source at the pinned commit used by this project.
"""

from __future__ import annotations

from dataclasses import dataclass

GLEAM_REPOSITORY = "un-fao/GLEAM"
GLEAM_PINNED_COMMIT = "90e416197e89093c4f3a347b263ba805d33d4aac"


@dataclass(frozen=True)
class GleamEmissionBundle:
    enteric_ch4_co2e_t: float
    manure_ch4_co2e_t: float
    manure_n2o_co2e_t: float
    feed_production_co2e_t: float
    other_livestock_co2e_t: float = 0.0

    @property
    def total_co2e_t(self) -> float:
        return (
            self.enteric_ch4_co2e_t
            + self.manure_ch4_co2e_t
            + self.manure_n2o_co2e_t
            + self.feed_production_co2e_t
            + self.other_livestock_co2e_t
        )


@dataclass(frozen=True)
class GleamProductionBundle:
    milk_kg: float = 0.0
    live_weight_gain_kg: float = 0.0
    eggs_kg: float = 0.0
    wool_kg: float = 0.0


@dataclass(frozen=True)
class GleamHerdResult:
    herd_id: str
    emissions: GleamEmissionBundle
    production: GleamProductionBundle


def aggregate_herds(results: list[GleamHerdResult]) -> GleamEmissionBundle:
    return GleamEmissionBundle(
        enteric_ch4_co2e_t=sum(item.emissions.enteric_ch4_co2e_t for item in results),
        manure_ch4_co2e_t=sum(item.emissions.manure_ch4_co2e_t for item in results),
        manure_n2o_co2e_t=sum(item.emissions.manure_n2o_co2e_t for item in results),
        feed_production_co2e_t=sum(item.emissions.feed_production_co2e_t for item in results),
        other_livestock_co2e_t=sum(item.emissions.other_livestock_co2e_t for item in results),
    )
