"""Streamlit dynamic dashboard for stage-by-stage dome assembly analysis."""
from __future__ import annotations

import time
import math
import numpy as np
import pandas as pd
import streamlit as st

from domestage.demo_model import generate_demo_dome
from domestage.schema import StructureModel, StageResult, SolveResult
from domestage.viz import create_dome_3d_figure, create_history_chart

# Page configuration
st.set_page_config(
    page_title="DomeStage · Simulación de Montaje",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom modern CSS styling
st.markdown(
    """
    <style>
        .main {
            background-color: #0b0f19;
            color: #f1f5f9;
        }
        .metric-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8));
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }
        .status-badge-stable {
            background-color: rgba(16, 185, 129, 0.2);
            color: #34d399;
            border: 1px solid #059669;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
        }
        .status-badge-unstable {
            background-color: rgba(239, 68, 68, 0.2);
            color: #f87171;
            border: 1px solid #dc2626;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
        }
        .highlight-val {
            font-size: 1.8rem;
            font-weight: 700;
            color: #38bdf8;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_dome_model(rings: int, sides: int, radius: float, height: float) -> StructureModel:
    return generate_demo_dome(rings=rings, sides=sides, radius=radius, total_height=height)


@st.cache_data
def precompute_stages(
    _model: StructureModel, bars_per_step: int = 1
) -> tuple[list[dict], dict[int, pd.Series]]:
    """Compute (or simulate) forces across all construction stages."""
    stages_order = sorted([st for st in _model.bars["stage"].unique() if st > 0])
    
    # Initial stage 0 (foundation/base ring)
    base_bars = _model.bars[_model.bars["stage"] == 0]["bar_id"].tolist()
    total_bars = len(_model.bars)
    
    stage_data = []
    forces_per_stage = {}
    
    active = list(base_bars)
    
    # Summary for stage 0
    init_forces = pd.Series(
        {b: -150.0 + 50.0 * math.sin(b) for b in active}
    )
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
    
    # Step through stages
    for st_num in stages_order:
        new_in_stage = _model.bars[_model.bars["stage"] == st_num]["bar_id"].tolist()
        active.extend(new_in_stage)
        
        # Synthetic physics simulation until analytical solver is plugged in:
        # Lower rings have more compression; as cantilever advances, compression and tension alternate.
        # Temporary unstable check (e.g. cantilever without triangulation)
        is_stable = True
        progress = len(active) / total_bars
        
        # Simulate axial forces (N)
        f_vals = {}
        for b in active:
            # base level compression accumulates with weight
            bar_row = _model.bars[_model.bars["bar_id"] == b].iloc[0]
            stage_weight = len(active) * 280.0
            z_factor = 1.0 - (bar_row.stage / (len(stages_order) + 1))
            val = -(stage_weight * z_factor) * 0.15 + (math.sin(b * 1.7) * 3500.0)
            if b in new_in_stage:
                # Extra installer load on the newest element
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
            "stable": is_stable,
            "new_bars": new_in_stage,
            "max_tension_kn": t_max,
            "max_compression_kn": c_max,
        })
        
    return stage_data, forces_per_stage


# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.image(
        "https://images.unsplash.com/photo-1541888946425-d0fbb18086f6?auto=format&fit=crop&w=400&q=80",
        use_container_width=True,
    )
    st.title("⚙️ Parámetros de Análisis")
    
    st.subheader("1. Modelo del Domo")
    rings = st.slider("Número de Anillos", min_value=2, max_value=8, value=4, step=1)
    sides = st.slider("Divisiones radiales (Lados)", min_value=6, max_value=24, value=12, step=2)
    radius = st.number_input("Radio base (m)", value=6.0, step=0.5)
    height = st.number_input("Altura total (m)", value=3.2, step=0.2)
    
    st.markdown("---")
    st.subheader("2. Cargas de Montaje")
    worker_load_kg = st.number_input("Peso instalador + herramienta (kg)", value=100.0, step=10.0)
    bars_step = st.selectbox("Avance por etapa", [1, 2, 3, 4], index=0)
    
    st.markdown("---")
    st.caption("🚀 Hackathon GEO 2026 · Análisis constructivo paso a paso")


# Load Model and compute stages
model = get_dome_model(rings=rings, sides=sides, radius=radius, height=height)
stage_history, forces_lookup = precompute_stages(model, bars_per_step=bars_step)

total_stages = len(stage_history) - 1
total_bars = len(model.bars)
total_nodes = len(model.nodes)

# --- TOP HEADER & PROGRESS BAR (0% - 100%) ---
st.title("🏗️ Simulación Dinámica de Montaje de Domo")
st.markdown("Revisión estructural paso a paso durante el proceso constructivo.")

# Initialize session state for animation / current stage
if "current_stage_idx" not in st.session_state:
    st.session_state.current_stage_idx = 0

# Timeline Controls
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 4, 1])

with col_ctrl1:
    btn_prev = st.button("◀ Etapa anterior", use_container_width=True)
    if btn_prev and st.session_state.current_stage_idx > 0:
        st.session_state.current_stage_idx -= 1

with col_ctrl3:
    btn_next = st.button("Etapa siguiente ▶", use_container_width=True)
    if btn_next and st.session_state.current_stage_idx < total_stages:
        st.session_state.current_stage_idx += 1

with col_ctrl2:
    # Interactive Slider for stages
    selected_stage = st.slider(
        "Etapa de Construcción (Análisis Activo)",
        min_value=0,
        max_value=total_stages,
        value=st.session_state.current_stage_idx,
        format="Etapa %d",
        key="slider_stage",
    )
    st.session_state.current_stage_idx = selected_stage

# Current stage data
current_info = stage_history[st.session_state.current_stage_idx]
progress_val = current_info["progress_pct"]

# Dynamic Progress Bar (0% to 100%)
st.markdown(f"**Progreso de Construcción del Domo:** `{progress_val}%` ({current_info['active_count']} de {total_bars} barras instaladas)")
st.progress(float(progress_val) / 100.0)

# Quick Metrics Cards
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div style="color: #94a3b8; font-size: 0.85rem;">ESTADO ESTRUCTURAL</div>
            <div style="margin-top: 6px;">
                <span class="{'status-badge-stable' if current_info['stable'] else 'status-badge-unstable'}">
                    {'● ESTABLE' if current_info['stable'] else '▲ MECANISMO / INESTABLE'}
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
            <div style="color: #94a3b8; font-size: 0.85rem;">BARRAS ACTIVAS</div>
            <div class="highlight-val">{current_info['active_count']} <span style="font-size: 1rem; color: #64748b;">/ {total_bars}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div style="color: #94a3b8; font-size: 0.85rem;">TRACCIÓN MÁXIMA</div>
            <div class="highlight-val" style="color: #38bdf8;">+{current_info['max_tension_kn']:.2f} <span style="font-size: 0.9rem;">kN</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div style="color: #94a3b8; font-size: 0.85rem;">COMPRESIÓN MÁXIMA</div>
            <div class="highlight-val" style="color: #f87171;">-{current_info['max_compression_kn']:.2f} <span style="font-size: 0.9rem;">kN</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# --- MAIN 3D VISUALIZATION & CHARTS ---
col_viz, col_data = st.columns([3, 2])

# Active bars in this stage
active_bars_current = []
for s_idx in range(st.session_state.current_stage_idx + 1):
    active_bars_current.extend(stage_history[s_idx]["new_bars"])
active_bars_current = list(set(active_bars_current))
new_bars_current = current_info["new_bars"]

curr_forces = forces_lookup.get(st.session_state.current_stage_idx, pd.Series())

with col_viz:
    st.subheader("🌐 Visualizador 3D en Tiempo Real")
    show_ghost = st.checkbox("Mostrar barras pendientes de instalar (estructura fantasma)", value=True)
    
    fig_3d = create_dome_3d_figure(
        model=model,
        active_bar_ids=active_bars_current,
        new_bar_ids=new_bars_current,
        axial_forces=curr_forces,
        show_future_bars=show_ghost,
    )
    st.plotly_chart(fig_3d, use_container_width=True, height=520)

with col_data:
    st.subheader("📈 Evolución de Esfuerzos")
    fig_hist = create_history_chart(stage_history, current_stage=st.session_state.current_stage_idx)
    st.plotly_chart(fig_hist, use_container_width=True)
    
    st.subheader(f"📋 Barras de la Etapa {st.session_state.current_stage_idx}")
    if new_bars_current:
        new_bars_df = model.bars[model.bars["bar_id"].isin(new_bars_current)].copy()
        new_bars_df["Axial (kN)"] = new_bars_df["bar_id"].map(lambda b: round(curr_forces.get(b, 0.0) / 1000.0, 2))
        st.dataframe(
            new_bars_df[["bar_id", "node_i", "node_j", "profile", "Axial (kN)"]].rename(
                columns={"bar_id": "ID Barra", "node_i": "Nodo I", "node_j": "Nodo J", "profile": "Perfil"}
            ),
            use_container_width=True,
            height=200,
        )
    else:
        st.info("Etapa inicial: Anillo base soportado.")
