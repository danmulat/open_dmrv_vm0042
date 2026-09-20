# SOC QRF and VM0042 implementation note

## Soil depth rule

The model uses a minimum SOC quantification depth of 30 cm. This applies to model inputs used for quantification and measured SOC values used for ex post stock change quantification under the active VM0042 methodology. Shallower legacy observations can be retained for calibration or validation only when the model output represents at least 30 cm and the extrapolation approach is documented.

Source: Verra, Reminder: Depth Requirements for Using Soil Carbon Data in VM0042 Projects, 21 October 2025.

https://verra.org/program-notice/reminder-depth-requirements-for-using-soil-carbon-data-in-vm0042-projects/

## Digital SOC reference workflow

The digital SOC module adapts the public Python workflow from Ecosystem Services GeoAI for Florida grazing lands. Transferable elements retained in the first implementation include time series feature engineering, Pearson correlation clustering, VIF screening, spatial grouped cross validation, RFECV, Random Forest parameter search, Quantile Regression Forest prediction, Q5 to Q95 quantiles, 90 percent prediction interval coverage, and later SHAP interpretation and raster mapping.

The Florida environmental datasets are not reused. Ethiopia and Kenya require local observations and regional covariates for the Omo Ghibe River Basin and Lake Victoria Basin. Spatial block size must be estimated from local spatial correlation rather than copied from Florida.

Reference repository:

https://github.com/Ecosystem-Services-GeoAI/florida-grazing-soc-qrf

Pinned reference commit:

48c3794256d88e87e3cc83bb66694a5f11bbbce0

## Livestock reference

The whole farm architecture pins FAO GLEAM to commit:

90e416197e89093c4f3a347b263ba805d33d4aac

The current gleam adapter defines the typed integration boundary. Full module translation from the pinned FAO source will be implemented incrementally. Existing IPCC Tier 2 helper equations are not treated as a substitute for GLEAM X.
