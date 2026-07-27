# Third Party Notices

## RothC_Py

The file `src/open_dmrv/models/rothc.py` contains modified carbon turnover code derived from the Rothamsted Research repository `Rothamsted-Models/RothC_Py`.

Original work copyright 2024 Rothamsted Research.

Licensed under the Apache License, Version 2.0. A copy of that license is available at:

https://www.apache.org/licenses/LICENSE-2.0

The adapted file retains the official monthly carbon pool equations, decomposition constants, temperature modifier, soil moisture deficit calculation, plant cover modifier, clay dependent carbon partitioning, plant input allocation and farmyard manure allocation.

The open dMRV adaptation adds a reusable Python object interface, measured SOC initialization, explicit pool initialization, scenario comparison, equilibrium spin up, monthly result objects, input validation and automated benchmark tests. Radiocarbon calculations are not included.

The original RothC_Py repository is available at:

https://github.com/Rothamsted-Models/RothC_Py
