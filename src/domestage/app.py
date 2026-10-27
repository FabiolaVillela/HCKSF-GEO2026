"""Streamlit app. OWNER: Role 5 or 6 (UI + demo).

Run: streamlit run src/domestage/app.py
Depends on: io_excel, io_dxf, stages, viz (only through their documented signatures).
"""
from __future__ import annotations

# TODO:
#  - Sidebar: upload Excel template (or DXF + parameters), bars_per_stage input.
#  - Run stages.run_stages (cache with st.cache_data).
#  - Slider for stage, viz.figure_3d, viz.figure_stage_history, results table.
#  - Download button using io_excel.export_results.
#  - Visible disclaimer: demonstration prototype, not for authorizing real assembly.
#  - Until other modules are ready, use fake StageResult data.
