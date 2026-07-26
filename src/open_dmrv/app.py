"""Optional Streamlit application."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Open dMRV", layout="wide")
st.title("Open dMRV synthetic Ethiopia dashboard")
st.warning("Research and synthetic data only. Not for carbon credit issuance.")

output = Path("outputs")
results_path = output / "annual_results.csv"
metrics_path = output / "validation_metrics.json"

if not results_path.exists() or not metrics_path.exists():
    st.info("Run `open-dmrv synthetic --output outputs` before opening this application.")
    st.stop()

results = pd.read_csv(results_path)
metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

columns = st.columns(4)
columns[0].metric("SOC RMSE", f"{metrics['rmse_t_c_ha']:.2f} t C per ha")
columns[1].metric("SOC MAE", f"{metrics['mae_t_c_ha']:.2f} t C per ha")
columns[2].metric("SOC bias", f"{metrics['bias_t_c_ha']:.2f} t C per ha")
columns[3].metric("R squared", f"{metrics['r_squared']:.3f}")

annual = results.groupby("year", as_index=False)["net_t_co2e"].sum()
st.line_chart(annual, x="year", y="net_t_co2e")
st.dataframe(results, use_container_width=True)
