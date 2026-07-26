# Open dMRV for VM0042 Measure and Model

This repository contains a research implementation of an open digital monitoring, reporting and verification system for integrated crop, livestock, pasture, tree and soil systems. The current release reproduces the logic of the accompanying Excel workbook in Python and includes a synthetic Ethiopian dataset for testing.

The model follows the structure of Verra VM0042 Quantification Approach 1, Measure and Model. It is designed to keep measured initial soil organic carbon stocks, baseline simulation, project simulation, repeated measurements, model validation and uncertainty accounting separate and traceable.

> **Research status:** This repository is not validated for carbon credit issuance. The RothC implementation, artificial intelligence components, remote sensing models, sampling plan and uncertainty deductions require independent review under the active Verra methodology and model guidance before use in a registered project.

![Modular platform](assets/modular_platform.png)

## Main modules

1. Soil organic carbon stock calculation from concentration, bulk density, depth and coarse fragments.
2. RothC style monthly process model for baseline and project SOC trajectories.
3. A process constrained interface for future RothC informed neural model development.
4. IPCC Tier 2 enteric methane calculations.
5. Manure methane and direct nitrous oxide calculations.
6. Soil nitrous oxide, woody biomass and farm energy calculations.
7. Crop yield, pasture productivity and animal productivity reporting.
8. Synthetic Ethiopian data generation and independent holdout validation.
9. Module level uncertainty and conservative result reporting.

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

## Generated outputs

Running the synthetic pipeline creates:

* `outputs/soc_measurements.csv`
* `outputs/soc_validation.csv`
* `outputs/validation_metrics.json`
* `outputs/annual_results.csv`
* `outputs/annual_results.png`
* `outputs/run_manifest.json`

## Synthetic Ethiopian test

The bundled dataset represents three illustrative strata:

* Central highland Nitisol mixed crop dairy system
* Mid altitude Vertisol crop livestock system
* Lower altitude Cambisol pasture crop livestock system

The synthetic SOC stocks are generated from depth specific SOC concentration, bulk density and coarse fragments. The values are intended to resemble plausible Ethiopian conditions, but they are not field observations and cannot be used for crediting.

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

## Workbook

The validated synthetic workbook is included at:

`workbook/Open_dMRV_VM0042_Synthetic_Ethiopia_Validated.xlsx`

![Dashboard preview](assets/dashboard_preview.png)

## Citation

Please use the information in `CITATION.cff` when citing the software.

## License

MIT License. See `LICENSE`.
