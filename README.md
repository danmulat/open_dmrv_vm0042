# Open dMRV for VM0042 Measure and Model

This repository contains a research implementation of an open digital monitoring, reporting and verification system for integrated crop, livestock, pasture, tree and soil systems. It includes a synthetic Ethiopian dataset for testing the full accounting workflow.

The model follows the structure of Verra VM0042 Quantification Approach 1, Measure and Model. It keeps measured initial soil organic carbon stocks, baseline simulation, project simulation, repeated measurements, model validation and uncertainty accounting separate and traceable.

> **Research status:** This repository is not validated for carbon credit issuance. The RothC parameterization, remote sensing models, sampling plan and uncertainty deductions require independent review under the active Verra methodology and model guidance before use in a registered project.

## Official RothC integration

The SOC module is now adapted from the official Rothamsted Research Python implementation, `Rothamsted-Models/RothC_Py`.

The implementation retains:

1. Monthly DPM, RPM, BIO, HUM and IOM carbon pools
2. Official decomposition constants
3. Official temperature rate modifier
4. Official accumulated soil moisture deficit calculation
5. Plant cover modifier
6. Clay dependent partitioning between carbon dioxide, BIO and HUM
7. Plant carbon partitioning through the DPM to RPM ratio
8. Farmyard manure partitioning to DPM, RPM and HUM
9. Equilibrium spin up and annual or monthly output

The official equilibrium example is included as an automated benchmark test. The model reproduces the published RothC_Py equilibrium total of `37.2110502645 t C per ha` and its component pools within numerical tolerance.

Radiocarbon calculations are not currently included because the dMRV accounting workflow uses carbon stocks and stock changes. See `THIRD_PARTY_NOTICES.md` for attribution and license details.

## Main modules

1. Soil organic carbon stock calculation from concentration, bulk density, depth and coarse fragments
2. Official RothC based monthly baseline and project SOC simulation
3. A process constrained interface for future RothC informed neural model development
4. IPCC Tier 2 enteric methane calculations
5. Manure methane and direct nitrous oxide calculations
6. Soil nitrous oxide, woody biomass and farm energy calculations
7. Crop yield, pasture productivity and animal productivity reporting
8. Synthetic Ethiopian data generation and independent holdout validation
9. Module level uncertainty and conservative result reporting

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
open-dmrv synthetic --output outputs
pytest
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

## RothC example

```python
from open_dmrv.models.rothc import RothCInputs, run_scenarios_from_same_initial

baseline_inputs = RothCInputs(
    temperatures_c=(18.0,) * 12,
    rainfall_mm=(100.0,) * 12,
    pet_mm=(80.0,) * 12,
    clay_percent=35.0,
    depth_cm=30.0,
    annual_plant_c_t_ha=3.0,
    annual_manure_c_t_ha=0.5,
    dpm_rpm_ratio=1.2,
    soil_cover=(True,) * 12,
)

project_inputs = RothCInputs(
    temperatures_c=(18.0,) * 12,
    rainfall_mm=(100.0,) * 12,
    pet_mm=(80.0,) * 12,
    clay_percent=35.0,
    depth_cm=30.0,
    annual_plant_c_t_ha=4.0,
    annual_manure_c_t_ha=1.0,
    dpm_rpm_ratio=1.2,
    soil_cover=(True,) * 12,
)

baseline, project = run_scenarios_from_same_initial(
    50.0,
    baseline_inputs,
    project_inputs,
    years=10,
)
```

`pet_mm` is retained for compatibility with the earlier package API, but it is interpreted as open pan evaporation to match the official RothC input variable `Evap`.

## Generated outputs

Running the synthetic pipeline creates:

* `outputs/soc_measurements.csv`
* `outputs/soc_validation.csv`
* `outputs/validation_metrics.json`
* `outputs/annual_results.csv`
* `outputs/annual_results.png`
* `outputs/run_manifest.json`

## Repository structure

```text
src/open_dmrv/       Python package
src/open_dmrv/models Accounting and process modules
data/synthetic/      Reproducible synthetic datasets
examples/            Example scripts
tests/               Unit and integration tests
docs/                Method and governance notes
workbook/             Excel implementation
assets/               Figures and previews
```

## License

The original open dMRV code is distributed under the MIT License. The adapted RothC module contains code derived from RothC_Py under the Apache License, Version 2.0. See `THIRD_PARTY_NOTICES.md`.
