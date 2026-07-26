"""End to end synthetic model pipeline."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import ModelConfig
from .models.biomass import woody_biomass_stock_co2e
from .models.energy import farm_energy_co2e
from .models.livestock import enteric_methane
from .models.manure import manure_emissions
from .models.soil_ghg import soil_n2o_emissions
from .models.uncertainty import illustrative_uncertainty_deduction
from .synthetic import STRATA, generate_soc_measurements, site_soc_stocks, synthetic_validation


def validation_metrics(validation: pd.DataFrame) -> dict[str, float]:
    observed = validation["observed_soc_t_c_ha"].to_numpy(dtype=float)
    predicted = validation["predicted_soc_t_c_ha"].to_numpy(dtype=float)
    residual = predicted - observed
    rmse = float(np.sqrt(np.mean(residual**2)))
    mae = float(np.mean(np.abs(residual)))
    bias = float(np.mean(residual))
    denominator = float(np.sum((observed - observed.mean()) ** 2))
    r_squared = 1.0 - float(np.sum(residual**2)) / denominator
    coverage = float(validation["covered_90_percent"].mean())
    return {"n": float(len(validation)), "mean_observed_soc_t_c_ha": float(observed.mean()), "rmse_t_c_ha": rmse, "mae_t_c_ha": mae, "bias_t_c_ha": bias, "r_squared": r_squared, "coverage_90_percent": coverage}


def _activity_parameters(stratum_id: str, year: int, scenario: str) -> dict[str, float]:
    elapsed = year - 2026
    effective = scenario == "Project" and elapsed > 0
    area = {"STR01": 500.0, "STR02": 700.0, "STR03": 800.0}[stratum_id]
    head_count = {"STR01": 120.0, "STR02": 90.0, "STR03": 70.0}[stratum_id]
    dmi = {"STR01": 9.5, "STR02": 8.0, "STR03": 6.5}[stratum_id] + ({"STR01": 0.6, "STR02": 0.5, "STR03": 0.3}[stratum_id] if effective else 0.0)
    ym = {"STR01": 6.5, "STR02": 6.6, "STR03": 6.8}[stratum_id] - ({"STR01": 0.5, "STR02": 0.6, "STR03": 0.7}[stratum_id] if effective else 0.0)
    return {
        "area": area,
        "head_count": head_count,
        "dmi": dmi,
        "ym": ym,
        "milk": {"STR01": 10.0, "STR02": 7.0, "STR03": 4.0}[stratum_id] + 0.1 * elapsed + (2.0 if effective else 0.0),
        "crop_yield": {"STR01": 2.7, "STR02": 2.2, "STR03": 1.5}[stratum_id] * (1.0 + 0.02 * elapsed) * (1.18 if effective else 1.0),
        "pasture": {"STR01": 4.8, "STR02": 4.0, "STR03": 3.2}[stratum_id] * (1.0 + 0.015 * elapsed) * (1.25 if effective else 1.0),
        "mineral_n": {"STR01": 65.0, "STR02": 50.0, "STR03": 30.0}[stratum_id] - (15.0 if effective else 0.0),
        "organic_n": {"STR01": 18.0, "STR02": 15.0, "STR03": 10.0}[stratum_id] + (15.0 if effective else 0.0),
        "residue_n": {"STR01": 22.0, "STR02": 20.0, "STR03": 14.0}[stratum_id] + (10.0 if effective else 0.0),
        "grazing_n": {"STR01": 16.0, "STR02": 20.0, "STR03": 28.0}[stratum_id] + (4.0 if effective else 0.0),
        "ef1": 0.010 - (0.0015 if effective else 0.0),
        "diesel": {"STR01": 32.0, "STR02": 24.0, "STR03": 14.0}[stratum_id] - (8.0 if effective else 0.0),
        "gasoline": {"STR01": 5.0, "STR02": 4.0, "STR03": 3.0}[stratum_id] - (1.0 if effective else 0.0),
        "vs": {"STR01": 3.8, "STR02": 3.2, "STR03": 2.6}[stratum_id] - (0.15 if effective else 0.0),
        "mcf": {"STR01": 12.0, "STR02": 10.0, "STR03": 8.0}[stratum_id] - (5.0 if effective else 0.0),
        "n_excretion": {"STR01": 0.26, "STR02": 0.22, "STR03": 0.18}[stratum_id],
        "ef3": 0.005 - (0.002 if effective else 0.0),
        "agb": {"STR01": 2.0, "STR02": 1.3, "STR03": 0.9}[stratum_id] + ({"STR01": 1.3, "STR02": 1.0, "STR03": 0.7}[stratum_id] * elapsed if scenario == "Project" else -0.03 * elapsed),
    }


def annual_results(site_stocks: pd.DataFrame, config: ModelConfig) -> pd.DataFrame:
    initial = site_stocks.groupby("stratum_id")["observed_soc_t_c_ha"].mean().to_dict()
    rates = {item.stratum_id: (item.baseline_soc_rate_t_c_ha_year, item.project_soc_rate_t_c_ha_year) for item in STRATA}
    rows: list[dict[str, float | int | str]] = []
    module_error_rates = {"soc": 0.08, "woody": 0.10, "enteric": 0.06, "manure": 0.08, "soil": 0.09, "energy": 0.07}
    for stratum in STRATA:
        for year in range(config.project.start_year, config.project.end_year + 1):
            elapsed = year - config.project.start_year
            baseline = _activity_parameters(stratum.stratum_id, year, "Baseline")
            project = _activity_parameters(stratum.stratum_id, year, "Project")
            baseline_soc = initial[stratum.stratum_id] + rates[stratum.stratum_id][0] * elapsed
            project_soc = initial[stratum.stratum_id] + rates[stratum.stratum_id][1] * elapsed
            soc_benefit = (project_soc - baseline_soc) * stratum.area_ha * config.constants.carbon_to_co2
            woody_benefit = (woody_biomass_stock_co2e(project["agb"]) - woody_biomass_stock_co2e(baseline["agb"])) * stratum.area_ha
            baseline_enteric = enteric_methane(baseline["head_count"], baseline["dmi"], 18.4, baseline["ym"], config.constants.gwp_ch4).co2e_t
            project_enteric = enteric_methane(project["head_count"], project["dmi"], 18.4, project["ym"], config.constants.gwp_ch4).co2e_t
            enteric_benefit = baseline_enteric - project_enteric
            baseline_manure = manure_emissions(baseline["head_count"], baseline["vs"], 0.24, baseline["mcf"], 100.0, baseline["n_excretion"], baseline["ef3"], config.constants.gwp_ch4, config.constants.gwp_n2o, config.constants.methane_density_kg_per_m3).total_co2e_t
            project_manure = manure_emissions(project["head_count"], project["vs"], 0.24, project["mcf"], 100.0, project["n_excretion"], project["ef3"], config.constants.gwp_ch4, config.constants.gwp_n2o, config.constants.methane_density_kg_per_m3).total_co2e_t
            manure_benefit = baseline_manure - project_manure
            baseline_soil = soil_n2o_emissions(baseline["area"], baseline["mineral_n"], baseline["organic_n"], baseline["residue_n"], baseline["grazing_n"], baseline["ef1"], config.constants.gwp_n2o).total_co2e_t
            project_soil = soil_n2o_emissions(project["area"], project["mineral_n"], project["organic_n"], project["residue_n"], project["grazing_n"], project["ef1"], config.constants.gwp_n2o).total_co2e_t
            soil_benefit = baseline_soil - project_soil
            energy_benefit = farm_energy_co2e(baseline["area"], baseline["diesel"], baseline["gasoline"]) - farm_energy_co2e(project["area"], project["diesel"], project["gasoline"])
            module_values = {"soc": soc_benefit, "woody": woody_benefit, "enteric": enteric_benefit, "manure": manure_benefit, "soil": soil_benefit, "energy": energy_benefit}
            gross = sum(module_values.values())
            deductions = sum(illustrative_uncertainty_deduction(value, abs(value) * module_error_rates[module], config.uncertainty.illustrative_threshold_percent).estimate - illustrative_uncertainty_deduction(value, abs(value) * module_error_rates[module], config.uncertainty.illustrative_threshold_percent).conservative_value for module, value in module_values.items())
            rows.append({"stratum_id": stratum.stratum_id, "year": year, "soc_t_co2e": soc_benefit, "woody_t_co2e": woody_benefit, "enteric_t_co2e": enteric_benefit, "manure_t_co2e": manure_benefit, "soil_ghg_t_co2e": soil_benefit, "farm_energy_t_co2e": energy_benefit, "gross_t_co2e": gross, "illustrative_uncertainty_deduction_t_co2e": deductions, "net_t_co2e": gross - deductions, "crop_yield_project_t_ha": project["crop_yield"], "pasture_project_t_dm_ha": project["pasture"], "milk_project_kg_cow_day": project["milk"]})
    return pd.DataFrame(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_synthetic_pipeline(output_directory: str | Path, config_path: str | Path = "config.yml", seed: int = 20260726) -> dict[str, Path]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    config = ModelConfig.from_yaml(config_path)
    measurements = generate_soc_measurements(seed)
    sites = site_soc_stocks(measurements)
    validation = synthetic_validation(sites)
    metrics = validation_metrics(validation)
    results = annual_results(sites, config)
    paths = {"measurements": output / "soc_measurements.csv", "validation": output / "soc_validation.csv", "metrics": output / "validation_metrics.json", "results": output / "annual_results.csv", "plot": output / "annual_results.png", "manifest": output / "run_manifest.json"}
    measurements.to_csv(paths["measurements"], index=False)
    validation.to_csv(paths["validation"], index=False)
    paths["metrics"].write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    results.to_csv(paths["results"], index=False)
    annual = results.groupby("year", as_index=False)["net_t_co2e"].sum()
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.plot(annual["year"], annual["net_t_co2e"], marker="o")
    axis.set_title("Synthetic annual net reductions and removals")
    axis.set_xlabel("Year")
    axis.set_ylabel("t CO2e")
    axis.grid(True, alpha=0.3)
    figure.tight_layout()
    figure.savefig(paths["plot"], dpi=160)
    plt.close(figure)
    manifest = {"created_at_utc": datetime.now(UTC).isoformat(), "package_status": "SYNTHETIC_TEST", "seed": seed, "config": config.model_dump(), "validation_metrics": metrics, "files": {}}
    for name, path in paths.items():
        if name != "manifest" and path.exists():
            manifest["files"][name] = {"path": str(path), "sha256": _sha256(path)}
    paths["manifest"].write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return paths
