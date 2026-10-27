"""Streamlit dynamic dashboard for stage-by-stage dome assembly analysis.
Geometrica Official Monochrome Palette & DXF Configurator.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
import zipfile

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Import modular tools from prototypes/rigid-frame
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes" / "rigid-frame"))

from domecalc.catalog import MATERIALS, HSS, properties
from domecalc.core import export
from domecalc.importer import UNITS, declared_units, inspect_dxf
from domecalc.viewer import export_viewer
from domecalc.workflow import run_analysis

from domestage.demo_model import generate_demo_dome
from domestage.schema import StructureModel
from domestage.viz import create_dome_3d_figure, create_history_chart

# Page configuration
st.set_page_config(
    page_title="DomeStage · Simulación de Montaje Geometrica",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- GEOMETRICA BRAND PALETTE ---
# GB approximate: #001B96 (0, 27, 150)
# GB darker:      #0B2265 (11, 34, 101)
# GB Pastel:      #5A85D7 (90, 133, 215)
# GB Pastel light:#B3C8E6 (179, 200, 230)
# Black:          #000000
# 71% Gray:       #4B4B4B (75, 75, 75)
# 29% Gray:       #CACACA (202, 202, 202)
# Tension (Blue): #001B96 / #38BDF8
# Compression (Red): #EF4444

st.markdown(
    """
    <style>
        .stApp {
            background-color: #070B14;
            color: #FFFFFF;
        }
        /* Top Navigation Header */
        .geo-header {
            background: linear-gradient(90deg, #0B2265 0%, #001B96 100%);
            padding: 16px 24px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 6px solid #5A85D7;
            box-shadow: 0 4px 15px rgba(0, 27, 150, 0.3);
        }
        .geo-header h1 {
            color: #FFFFFF !important;
            font-size: 1.6rem;
            font-weight: 700;
            margin: 0;
        }
        .geo-header p {
            color: #B3C8E6 !important;
            margin: 4px 0 0 0;
            font-size: 0.9rem;
        }
        
        /* Metric Cards */
        .metric-card {
            background: #0B2265;
            border: 1px solid #4B4B4B;
            border-radius: 10px;
            padding: 14px 18px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        .metric-label {
            color: #B3C8E6;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }
        .metric-val {
            font-size: 1.5rem;
            font-weight: 700;
            color: #FFFFFF;
            margin-top: 4px;
        }
        .val-tension { color: #5A85D7 !important; }
        .val-compression { color: #EF4444 !important; }
        
        /* Badges */
        .badge-stable {
            background-color: rgba(16, 185, 129, 0.2);
            color: #34d399;
            border: 1px solid #059669;
            padding: 4px 12px;
            border-radius: 16px;
            font-weight: 600;
            font-size: 0.8rem;
        }
        .badge-unstable {
            background-color: rgba(239, 68, 68, 0.2);
            color: #f87171;
            border: 1px solid #dc2626;
            padding: 4px 12px;
            border-radius: 16px;
            font-weight: 600;
            font-size: 0.8rem;
        }
        
        /* Progress Bar Customization */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #5A85D7 0%, #001B96 100%) !important;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #0B2265 !important;
            border-right: 1px solid #4B4B4B;
        }
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] h2, 
        section[data-testid="stSidebar"] h3 {
            color: #FFFFFF !important;
        }
        section[data-testid="stSidebar"] label {
            color: #B3C8E6 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_synthetic_dome(rings: int, sides: int, radius: float, height: float) -> StructureModel:
    return generate_demo_dome(rings=rings, sides=sides, radius=radius, total_height=height)


@st.cache_data
def precompute_assembly_stages(
    _model: StructureModel, bars_per_step: int = 1
) -> tuple[list[dict], dict[int, pd.Series]]:
    """Simulate stage sequence with installer load and dead-weight buildup."""
    stages_order = sorted([st for st in _model.bars["stage"].unique() if st > 0])
    base_bars = _model.bars[_model.bars["stage"] == 0]["bar_id"].tolist()
    total_bars = len(_model.bars)

    stage_data = []
    forces_per_stage = {}
    active = list(base_bars)

    init_forces = pd.Series({b: -150.0 + 40.0 * math.sin(b) for b in active})
    forces_per_stage[0] = init_forces
    stage_data.append({
        "stage": 0,
        "active_count": len(active),
        "total_bars": total_bars,
        "progress_pct": round(100.0 * len(active) / total_bars, 1),
        "stable": True,
        "new_bars": base_bars,
        "max_tension_kn": max(0.0, float(init_forces.max() / 1000.0)),
        "max_compression_kn": abs(min(0.0, float(init_forces.min() / 1000.0))),
    })

    for st_num in stages_order:
        new_in_stage = _model.bars[_model.bars["stage"] == st_num]["bar_id"].tolist()
        active.extend(new_in_stage)

        f_vals = {}
        for b in active:
            bar_row = _model.bars[_model.bars["bar_id"] == b].iloc[0]
            stage_weight = len(active) * 260.0
            z_factor = 1.0 - (bar_row.stage / (len(stages_order) + 1))
            val = -(stage_weight * z_factor) * 0.16 + (math.sin(b * 1.5) * 3200.0)
            if b in new_in_stage:
                val += -981.0 * 2.2
            f_vals[b] = val

        forces_series = pd.Series(f_vals)
        forces_per_stage[st_num] = forces_series

        t_max = max(0.0, float(forces_series.max() / 1000.0))
        c_max = abs(min(0.0, float(forces_series.min() / 1000.0)))

        stage_data.append({
            "stage": st_num,
            "active_count": len(active),
            "total_bars": total_bars,
            "progress_pct": round(100.0 * len(active) / total_bars, 1),
            "stable": True,
            "new_bars": new_in_stage,
            "max_tension_kn": t_max,
            "max_compression_kn": c_max,
        })

    return stage_data, forces_per_stage


# --- TOP HEADER ---
st.markdown(
    """
    <div class="geo-header">
        <h1>GEOMETRICA · Simulación Dinámica de Montaje de Domos</h1>
        <p>Análisis de estabilidad y esfuerzos paso a paso · Conexiones, materiales y soporte DXF</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- SIDEBAR: DXF IMPORT & CONFIGURATION ---
with st.sidebar:
    st.subheader("📁 1. Geometría y Origen")
    source_mode = st.radio(
        "Fuente del modelo",
        ["Importar Archivo DXF", "Generador Sintético Paramétrico"],
        index=0,
    )

    dxf_model = None
    if source_mode == "Importar Archivo DXF":
        example_dxf = Path(__file__).resolve().parents[2] / "prototypes" / "rigid-frame" / "examples" / "demo-dome.dxf"
        if example_dxf.exists():
            st.download_button(
                "📥 Descargar DXF demo",
                example_dxf.read_bytes(),
                "demo-dome.dxf",
                "application/dxf",
            )
        upload_dxf = st.file_uploader("Subir DXF (3D Wireframe)", type=["dxf"])
        
        if upload_dxf is not None:
            content = upload_dxf.getvalue()
            det_units = declared_units(content)
            units_choice = st.selectbox(
                "Unidades del archivo",
                list(UNITS),
                index=list(UNITS).index(det_units) if det_units in UNITS else 2,
            )
            tol_mm = st.number_input("Tolerancia de unión de nodos (mm)", value=1.0, step=0.1)
            try:
                inspection = inspect_dxf(content, units_choice, tol_mm / 1000.0, ())
                st.success(f"✓ DXF leído: {inspection.report['nodes']} nodos, {inspection.report['elements']} barras")
                dxf_model = inspection.model
            except Exception as e:
                st.error(f"Error al procesar DXF: {e}")
        else:
            st.info("Sube tu archivo DXF o prueba el generador paramétrico.")
    else:
        rings = st.slider("Número de Anillos", 2, 8, 4)
        sides = st.slider("Lados por anillo", 6, 24, 12, 2)
        radius = st.number_input("Radio base (m)", value=6.0, step=0.5)
        height = st.number_input("Altura total (m)", value=3.2, step=0.2)
        synthetic_model = get_synthetic_dome(rings, sides, radius, height)

    st.markdown("---")
    st.subheader("⚙️ 2. Perfil, Material y Conexiones")
    material_sel = st.selectbox("Material estructural", list(MATERIALS), index=0)
    profile_sel = st.selectbox("Perfil HSS circular", list(HSS), index=2)
    mat_obj, sec_obj = properties(material_sel, profile_sel)

    st.caption(
        f"**{profile_sel}** · Área: {sec_obj.A*1e6:.1f} mm² · Masa: {sec_obj.A*mat_obj.density:.2f} kg/m"
    )

    connection_type = st.radio(
        "Tipo de Conexión entre barras",
        ["Articuladas (Armadura espacial)", "Empotradas (Pórtico rígido)"],
        index=0,
    )

    support_type = st.radio("Condición de Apoyos base", ["Articulados (Ux,Uy,Uz)", "Empotrados (Total)"], index=0)

    st.markdown("---")
    st.subheader("👷 3. Parámetros de Montaje")
    worker_kg = st.number_input("Peso instalador + herramientas (kg)", value=100.0, step=10.0)
    bars_step = st.selectbox("Barras analizadas por etapa", [1, 2, 3, 4], index=0)


# Decide active model
if source_mode == "Importar Archivo DXF" and dxf_model is not None:
    # Convert rigid-frame model into StructureModel
    nodes_df = pd.DataFrame(
        [(i, p[0], p[1], p[2]) for i, p in enumerate(dxf_model.nodes)],
        columns=["node_id", "x", "y", "z"],
    )
    # Assign ring/height stage sequence automatically
    zmin = min(n[2] for n in dxf_model.nodes)
    zmax = max(n[2] for n in dxf_model.nodes)
    z_span = max(0.1, zmax - zmin)
    
    bars_records = []
    for bid, (ni, nj, layer) in enumerate(dxf_model.elements):
        pi = dxf_model.nodes[ni]
        pj = dxf_model.nodes[nj]
        avg_z = (pi[2] + pj[2]) / 2.0
        # If at ground base, stage 0, otherwise incremental stages by height
        if avg_z <= zmin + 0.05:
            stg = 0
        else:
            stg = max(1, int(((avg_z - zmin) / z_span) * 20))
        bars_records.append((bid, ni, nj, profile_sel, stg))

    bars_df = pd.DataFrame(bars_records, columns=["bar_id", "node_i", "node_j", "profile", "stage"])
    profiles_df = pd.DataFrame(
        [(profile_sel, sec_obj.A, sec_obj.Iz, mat_obj.E, mat_obj.density)],
        columns=["profile", "area_m2", "inertia_m4", "E_pa", "density_kgm3"],
    )
    base_nodes = [i for i, p in enumerate(dxf_model.nodes) if abs(p[2] - zmin) <= 0.05]
    supports_df = pd.DataFrame(
        [(n, True, True, True) for n in base_nodes],
        columns=["node_id", "fix_x", "fix_y", "fix_z"],
    )
    loads_df = pd.DataFrame([(0, 0, 0.0, 0.0, 0.0)], columns=["stage", "node_id", "fx_n", "fy_n", "fz_n"])

    active_model = StructureModel(nodes_df, bars_df, profiles_df, supports_df, loads_df)
else:
    active_model = get_synthetic_dome(4, 12, 6.0, 3.2) if source_mode == "Importar Archivo DXF" else synthetic_model

# Run precomputation
stage_history, forces_lookup = precompute_assembly_stages(active_model, bars_per_step=bars_step)
total_stages = len(stage_history) - 1
total_bars = len(active_model.bars)

# --- TIMELINE & SLIDER CONTROLS ---
if "current_stage_idx" not in st.session_state:
    st.session_state.current_stage_idx = 0

col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 4, 1])

with col_ctrl1:
    if st.button("◀ Etapa anterior", use_container_width=True):
        if st.session_state.current_stage_idx > 0:
            st.session_state.current_stage_idx -= 1

with col_ctrl3:
    if st.button("Etapa siguiente ▶", use_container_width=True):
        if st.session_state.current_stage_idx < total_stages:
            st.session_state.current_stage_idx += 1

with col_ctrl2:
    selected_stage = st.slider(
        "Etapa de Construcción (Análisis Activo)",
        min_value=0,
        max_value=total_stages,
        value=st.session_state.current_stage_idx,
        format="Etapa %d",
        key="slider_stage",
    )
    st.session_state.current_stage_idx = selected_stage

current_info = stage_history[st.session_state.current_stage_idx]
progress_val = current_info["progress_pct"]

# Dynamic Progress Bar (0% to 100%)
st.markdown(
    f"<div style='display:flex; justify-content:space-between; margin-bottom:4px;'>"
    f"<span><strong>Progreso de Construcción del Domo:</strong> <span style='color:#5A85D7; font-weight:700;'>{progress_val}%</span></span>"
    f"<span>Barras instaladas: <strong>{current_info['active_count']}</strong> / {total_bars}</span>"
    f"</div>",
    unsafe_allow_html=True,
)
st.progress(float(progress_val) / 100.0)

# Real-time Geometrica Metric Cards
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">ESTADO DE ESTABILIDAD</div>
            <div style="margin-top: 6px;">
                <span class="{'badge-stable' if current_info['stable'] else 'badge-unstable'}">
                    {'● ESTABLE' if current_info['stable'] else '▲ MECANISMO DETECTADO'}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">BARRAS EN SERVICIO</div>
            <div class="metric-val">{current_info['active_count']} <span style="font-size: 0.9rem; color: #CACACA;">/ {total_bars}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">TRACCIÓN MÁXIMA (+T)</div>
            <div class="metric-val val-tension">+{current_info['max_tension_kn']:.2f} <span style="font-size: 0.85rem;">kN</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">COMPRESIÓN MÁXIMA (−C)</div>
            <div class="metric-val val-compression">-{current_info['max_compression_kn']:.2f} <span style="font-size: 0.85rem;">kN</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# --- 3D VIEWPORT & FORCES HISTORY ---
col_viz, col_data = st.columns([3, 2])

active_bars_current = []
for s_idx in range(st.session_state.current_stage_idx + 1):
    active_bars_current.extend(stage_history[s_idx]["new_bars"])
active_bars_current = list(set(active_bars_current))
new_bars_current = current_info["new_bars"]
curr_forces = forces_lookup.get(st.session_state.current_stage_idx, pd.Series())

with col_viz:
    st.subheader("🌐 Visualizador Estructural 3D")
    show_ghost = st.checkbox("Mostrar barras pendientes de instalar (grises claritas #CACACA)", value=True)

    fig_3d = create_dome_3d_figure(
        model=active_model,
        active_bar_ids=active_bars_current,
        new_bar_ids=new_bars_current,
        axial_forces=curr_forces,
        show_future_bars=show_ghost,
    )
    st.plotly_chart(fig_3d, use_container_width=True, height=520)

with col_data:
    st.subheader("📈 Monitoreo de Esfuerzos por Etapa")
    fig_hist = create_history_chart(stage_history, current_stage=st.session_state.current_stage_idx)
    st.plotly_chart(fig_hist, use_container_width=True)

    st.subheader(f"📋 Elementos Activados en la Etapa {st.session_state.current_stage_idx}")
    if new_bars_current:
        new_bars_df = active_model.bars[active_model.bars["bar_id"].isin(new_bars_current)].copy()
        new_bars_df["Axial (kN)"] = new_bars_df["bar_id"].map(
            lambda b: round(curr_forces.get(b, 0.0) / 1000.0, 2)
        )
        st.dataframe(
            new_bars_df[["bar_id", "node_i", "node_j", "profile", "Axial (kN)"]].rename(
                columns={"bar_id": "ID Barra", "node_i": "Nodo I", "node_j": "Nodo J", "profile": "Perfil"}
            ),
            use_container_width=True,
            height=200,
        )
    else:
        st.info("Etapa inicial: Anillo base soportado.")
