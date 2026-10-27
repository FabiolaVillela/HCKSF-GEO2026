"""Combined construction-stage dashboard.

Real analysis (stages.run_stages) from feature/app-demo, with the dashboard layout of
feature/dynamic-ui (branded header, progress bar, metric cards, previous/next stepping,
material and HSS catalog) and the extras of feature/app (disclaimer, limitations,
Excel downloads).
"""
from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from .demo import generate_dome
from .io_dxf import assign_stages_by_height, detect_base_supports, read_dxf
from .io_excel import export_results, read_template, write_template
from .schema import G, LOADS_COLS, PROFILES_COLS, StructureModel, validate_model
from .stages import run_stages
from .viz import figure_3d, figure_stage_history

BLUE, DARK, PASTEL, GRAY = "#001B96", "#0B2265", "#5A85D7", "#CACACA"
GHOST = "#dddddd"  # color figure_3d gives to bars not yet installed
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

CSS = f"""
<style>
.dash-header {{background: linear-gradient(90deg, {DARK}, {BLUE}); padding: 14px 22px;
  border-radius: 10px; border-left: 6px solid {PASTEL}; margin-bottom: 14px;}}
.dash-header h1 {{color: #fff !important; font-size: 1.5rem; margin: 0; padding: 0;}}
.dash-header p {{color: #B3C8E6; margin: 4px 0 0 0; font-size: .9rem;}}
.dash-card {{background: {DARK}; border: 1px solid #4B4B4B; border-radius: 10px;
  padding: 12px 16px; min-height: 84px;}}
.dash-label {{color: #B3C8E6; font-size: .75rem; text-transform: uppercase;
  letter-spacing: .5px; font-weight: 600;}}
.dash-value {{color: #fff; font-size: 1.45rem; font-weight: 700; margin-top: 4px;}}
.dash-ok {{background: rgba(16,185,129,.2); color: #34d399; border: 1px solid #059669;
  padding: 4px 12px; border-radius: 16px; font-weight: 600; font-size: .85rem;}}
.dash-bad {{background: rgba(239,68,68,.2); color: #f87171; border: 1px solid #dc2626;
  padding: 4px 12px; border-radius: 16px; font-weight: 600; font-size: .85rem;}}
</style>
"""


def _card(label: str, value: str) -> str:
    return f'<div class="dash-card"><div class="dash-label">{label}</div>{value}</div>'


@st.cache_data(show_spinner=False)
def _analyze(model: StructureModel, batch: int):
    return run_stages(model, batch)


@st.cache_data(show_spinner=False)
def _excel(kind: str, payload) -> bytes:
    stream = io.BytesIO()
    (write_template if kind == "model" else export_results)(payload, stream)
    return stream.getvalue()


def _apply_profile(model: StructureModel, material: str, hss: str, worker_kg: float) -> StructureModel:
    """Replace the profile table with the chosen catalog section; set the installer weight."""
    from domecalc.catalog import properties  # prototypes/rigid-frame is put on sys.path by app.py

    mat, sec = properties(material, hss)
    profiles = pd.DataFrame(
        [("TUBE", sec.A, sec.Iz, mat.E, mat.density)], columns=PROFILES_COLS
    )
    bars = model.bars.assign(profile="TUBE")
    loads = model.loads.copy()
    loads.loc[loads["fz_n"] != 0, "fz_n"] = -worker_kg * G
    return StructureModel(model.nodes, bars, profiles, model.supports, loads, model.criteria)


def _load_model(source: str, uploaded, params: dict) -> StructureModel | None:
    if source == "Synthetic dome":
        return generate_dome(params["rings"], params["sides"], params["radius"])
    if uploaded is None:
        return None
    if uploaded.size > 5 * 1024 * 1024:
        raise ValueError("Use a model file smaller than 5 MB for this prototype.")
    if source == "Excel template":
        return read_template(io.BytesIO(uploaded.getvalue()))  # profiles come from the file
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.dxf"
        path.write_bytes(uploaded.getvalue())
        layers = tuple(x.strip() for x in params["layers"].split(",") if x.strip())
        nodes, bars = read_dxf(path, params["unit_scale"], layers=layers)
    bars = assign_stages_by_height(nodes, bars, params["ring_height"])
    heights = nodes.set_index("node_id").z
    loads = []
    for stage, group in bars.groupby("stage"):
        if stage > 0:
            ends = sorted(set(group.node_i) | set(group.node_j))
            loads.append((int(stage), heights.loc[ends].idxmax(), 0.0, 0.0, -1.0))
    profiles = pd.DataFrame([("TUBE", 1e-3, 1e-6, 200e9, 7850.0)], columns=PROFILES_COLS)
    return StructureModel(nodes, bars, profiles, detect_base_supports(nodes),
                          pd.DataFrame(loads, columns=LOADS_COLS))


def _step_by(delta: int, last: int) -> None:
    st.session_state.dash_step = min(max(st.session_state.get("dash_step", 0) + delta, 0), last)


def render() -> None:
    from domecalc.catalog import HSS, MATERIALS

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="dash-header"><h1>Dome erection · stage-by-stage analysis</h1>'
        "<p>Stability and member forces after each installed group of bars</p></div>",
        unsafe_allow_html=True,
    )
    st.warning("Demonstration prototype. Do not use these results to authorize a real assembly.")

    params: dict = {}
    with st.sidebar:
        st.subheader("1. Model")
        source = st.selectbox("Model source", ["Synthetic dome", "Excel template", "DXF wireframe"],
                              key="dash_source")
        uploaded = None
        if source != "Synthetic dome":
            uploaded = st.file_uploader("Upload model", type=["xlsx"] if source == "Excel template" else ["dxf"],
                                        key="dash_upload")
        if source == "Synthetic dome":
            params["rings"] = int(st.number_input("Dome rings", 1, 5, 3, key="dash_rings"))
            params["sides"] = int(st.number_input("Nodes per ring", 3, 16, 8, key="dash_sides"))
            params["radius"] = st.number_input("Dome radius (m)", min_value=0.1, value=5.0, key="dash_radius")
        elif source == "DXF wireframe":
            params["unit_scale"] = st.number_input("Meters per DXF unit", min_value=1e-6, value=1.0,
                                                   format="%.6f", key="dash_unit")
            params["ring_height"] = st.number_input("Stage height interval (m)", min_value=0.001, value=1.0,
                                                    key="dash_ring")
            params["layers"] = st.text_input("Layers (comma separated; blank = all)", key="dash_layers")

        st.subheader("2. Section and loads")
        from_catalog = source != "Excel template"
        if from_catalog:
            material = st.selectbox("Material", list(MATERIALS), key="dash_material")
            hss = st.selectbox("Circular HSS profile", list(HSS), index=2, key="dash_hss")
            worker_kg = st.number_input("Installer + tools (kg)", min_value=0.0, value=100.0, step=10.0,
                                        key="dash_worker")
        else:
            st.caption("Sections and loads come from the Excel file.")

        st.subheader("3. Stages")
        batch = int(st.number_input("Bars installed per stage", 1, 500, 1, key="dash_batch"))

    try:
        model = _load_model(source, uploaded, params)
        if model is None:
            st.info("Upload a model, or choose Synthetic dome to run the example.")
            return
        if from_catalog:
            model = _apply_profile(model, material, hss, worker_kg)
        problems = validate_model(model)
        if problems:
            raise ValueError("; ".join(problems))
        if len(model.nodes) > 250 or len(model.bars) > 500:
            raise ValueError("Interactive prototype limit: 250 nodes and 500 bars")
        with st.spinner("Analyzing construction stages…"):
            results = _analyze(model, batch)
    except Exception as error:  # parsers raise several exception types
        st.error(f"Cannot analyze this model: {error}")
        return

    last = len(results) - 1
    if st.session_state.get("dash_step", 0) > last:
        st.session_state.dash_step = last
    st.session_state.setdefault("dash_step", 0)

    prev_col, slider_col, next_col = st.columns([1, 5, 1])
    prev_col.button("◀ Previous", on_click=_step_by, args=(-1, last), width="stretch",
                    disabled=st.session_state.dash_step <= 0)
    next_col.button("Next ▶", on_click=_step_by, args=(1, last), width="stretch",
                    disabled=st.session_state.dash_step >= last)
    with slider_col:
        if last > 0:
            st.slider("Construction stage", 0, last, key="dash_step")
        else:
            st.caption("Only one stage in this model.")
    sr = results[st.session_state.dash_step]
    r = sr.result

    installed, total = len(sr.active_bars), len(model.bars)
    st.progress(installed / total, text=f"Installed {installed} of {total} bars "
                                        f"({100 * installed / total:.0f}%)")
    unstable = sum(not s.result.stable for s in results)
    tension = compression = None
    if r.stable and r.axial_force_n.notna().any():
        tension = max(0.0, float(r.axial_force_n.max())) / 1000
        compression = max(0.0, -float(r.axial_force_n.min())) / 1000
    badge = ('<span class="dash-ok">● STABLE</span>' if r.stable
             else '<span class="dash-bad">▲ MECHANISM</span>')
    fmt = lambda v: "n/a" if v is None else f"{v:.2f} kN"  # noqa: E731
    cols = st.columns(4)
    cols[0].markdown(_card("Stability", f'<div style="margin-top:8px">{badge}</div>'), unsafe_allow_html=True)
    cols[1].markdown(_card("Unstable stages (all)", f'<div class="dash-value">{unstable} / {len(results)}</div>'),
                     unsafe_allow_html=True)
    cols[2].markdown(_card("Max tension", f'<div class="dash-value" style="color:{PASTEL}">{fmt(tension)}</div>'),
                     unsafe_allow_html=True)
    cols[3].markdown(_card("Max compression",
                           f'<div class="dash-value" style="color:#f87171">{fmt(compression)}</div>'),
                     unsafe_allow_html=True)

    if r.stable:
        st.success(f"Stage {sr.stage}: stable linear equilibrium. {len(sr.new_bars)} bars added.")
    else:
        st.error(f"Stage {sr.stage}: unstable — {r.message}. Forces and displacements are unavailable.")

    left, right = st.columns([3, 2])
    with left:
        c1, c2, c3 = st.columns(3)
        color = c1.selectbox("Color bars by", ["stress", "force", "utilization", "buckling"], key="dash_color")
        scale = c2.slider("Deformation ×", 0, 5000, 0, step=100, key="dash_scale")
        ghost = c3.checkbox("Show uninstalled bars", value=True, key="dash_ghost")
        fig = figure_3d(model, sr, color, scale)
        if not ghost:
            fig.data = tuple(t for t in fig.data if getattr(t.line, "color", None) != GHOST)
        st.plotly_chart(fig, width="stretch")
    with right:
        metric = st.selectbox("History metric", ["max_force", "max_stress", "max_disp", "max_buckling"],
                              key="dash_metric")
        hist = figure_stage_history(results, metric)
        hist.add_vline(x=sr.stage, line_dash="dot", line_color=PASTEL)
        hist.update_layout(height=330, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(hist, width="stretch")

    bars_tab, nodes_tab, input_tab = st.tabs(["Bar results", "Displacements and reactions", "Input model"])
    with bars_tab:
        table = pd.DataFrame({"bar_id": sr.active_bars})
        table["new"] = table.bar_id.isin(sr.new_bars)
        table["force_n"] = table.bar_id.map(r.axial_force_n)
        table["stress_mpa"] = table.bar_id.map(r.stress_pa) / 1e6
        if r.buckling_ratio is not None:
            table["buckling_ratio"] = table.bar_id.map(r.buckling_ratio)
        st.dataframe(table, hide_index=True, width="stretch")
    with nodes_tab:
        st.dataframe(r.displacements, hide_index=True, width="stretch")
        st.dataframe(r.reactions, hide_index=True, width="stretch")
    with input_tab:
        for name in ["nodes", "bars", "profiles", "supports", "loads"]:
            st.write(name.title())
            st.dataframe(getattr(model, name), hide_index=True, width="stretch")

    d1, d2 = st.columns(2)
    d1.download_button("Download model (Excel template)", _excel("model", model), "dome-model.xlsx", XLSX)
    d2.download_button("Download all stage results (Excel)", _excel("results", results),
                       "dome-stage-results.xlsx", XLSX)

    with st.expander("Limitations"):
        st.markdown(
            "- Pin-jointed truss: may flag as unstable a structure that stands thanks to rigid joints.\n"
            "- Each stage is solved from scratch: no shoring, cranes or assembly history.\n"
            "- No P-Δ, connection capacity or code-based checks; buckling is a simple Euler ratio.\n"
            "- Not a safety approval."
        )
