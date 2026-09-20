"""Configuration models and constants."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    name: str
    country: str = "Ethiopia"
    start_year: int = 2026
    end_year: int = 2030
    soc_depth_cm: float = Field(default=30.0, ge=30.0)
    confidence_level_percent: float = 90.0
    precision_target_percent: float = 10.0
    status: str = "RESEARCH"


class Constants(BaseModel):
    carbon_to_co2: float = 44.0 / 12.0
    gwp_ch4: float = 27.2
    gwp_n2o: float = 273.0
    methane_energy_mj_per_kg: float = 55.65
    methane_density_kg_per_m3: float = 0.67


class MethodologyConfig(BaseModel):
    vm0042_version: str = "2.2"
    vmd0053_version: str = "2.1"
    vt0014_version: str = "1.0"
    gleam_repository: str = "un-fao/GLEAM"
    gleam_commit: str = "90e416197e89093c4f3a347b263ba805d33d4aac"
    digital_soc_reference_repository: str = (
        "Ecosystem-Services-GeoAI/florida-grazing-soc-qrf"
    )
    digital_soc_reference_commit: str = "48c3794256d88e87e3cc83bb66694a5f11bbbce0"


class UncertaintyConfig(BaseModel):
    illustrative_threshold_percent: float = Field(default=15.0, ge=0.0)


class ModelConfig(BaseModel):
    project: ProjectConfig
    constants: Constants = Constants()
    methodology: MethodologyConfig = MethodologyConfig()
    uncertainty: UncertaintyConfig = UncertaintyConfig()

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ModelConfig":
        with Path(path).open("r", encoding="utf-8") as stream:
            return cls.model_validate(yaml.safe_load(stream))
