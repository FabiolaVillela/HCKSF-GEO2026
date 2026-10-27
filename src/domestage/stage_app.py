"""Construction-stage Streamlit interface using the shared truss contract."""
from __future__ import annotations
import io
import tempfile
from pathlib import Path
import pandas as pd
import streamlit as st
from .demo import generate_dome
from .io_dxf import read_dxf, assign_stages_by_height, detect_base_supports
from .io_excel import read_template, write_template, export_results
from .schema import StructureModel, PROFILES_COLS, LOADS_COLS, validate_model
from .stages import run_stages
from .viz import figure_3d, figure_stage_history


@st.cache_data(show_spinner=False)
def analyze_stages(model, batch):
    return run_stages(model, batch)


@st.cache_data(show_spinner=False)
def model_excel(model):
    stream = io.BytesIO()
    write_template(model, stream)
    return stream.getvalue()


@st.cache_data(show_spinner=False)
def results_excel(results):
    stream = io.BytesIO()
    export_results(results, stream)
    return stream.getvalue()


def render():
    st.title('Stage-by-stage steel dome analysis')
    st.warning('Demonstration only. Do not use these results to authorize construction or structural design.')
    st.caption('3D pin-jointed truss · axial forces only · SI units · tension positive')
    with st.sidebar:
        source = st.selectbox('Model source', ['Synthetic dome', 'Excel template', 'DXF wireframe'])
        uploaded = None
        if source != 'Synthetic dome':
            uploaded = st.file_uploader('Upload model', type=['xlsx'] if source == 'Excel template' else ['dxf'])
        batch = st.number_input('Bars installed per analysis step', min_value=1, max_value=500, value=8, step=1)
        if source == 'Synthetic dome':
            rings = st.number_input('Dome rings', min_value=1, max_value=5, value=3, step=1)
            sides = st.number_input('Nodes per ring', min_value=3, max_value=16, value=8, step=1)
            radius = st.number_input('Dome radius (m)', min_value=.1, value=5.)
        elif source == 'DXF wireframe':
            st.caption('Straight LINE/POLYLINE entities. Curves, blocks and disconnected structures are rejected.')
            unit_scale = st.number_input('Meters per DXF unit', min_value=.000001, value=1., format='%.6f')
            ring_height = st.number_input('Stage height interval (m)', min_value=.001, value=1.)
            layers = st.text_input('Layers to import (comma separated; blank = all)')
            area = st.number_input('Bar area (cm²)', min_value=.001, value=5.)
            inertia = st.number_input('Bar second moment of area (cm⁴)', min_value=0., value=50.)
            modulus = st.number_input('Elastic modulus (GPa)', min_value=1., value=200.)
            installation = st.number_input('Installation load (kN downward)', min_value=0., value=1.)
            st.caption('Steel density 7850 kg/m³; yield stress 250 MPa. All base translations fixed. '
                       'One installation load per source stage at its highest endpoint. '
                       'Download and edit the Excel model to customize these assumptions.')
    try:
        if source == 'Synthetic dome':
            model = generate_dome(int(rings), int(sides), radius)
        elif uploaded is None:
            st.info('Upload a model, or choose Synthetic dome to run the example.')
            return
        elif uploaded.size > 5 * 1024 * 1024:
            st.error('Use a model file smaller than 5 MB for this prototype.')
            return
        elif source == 'Excel template':
            model = read_template(io.BytesIO(uploaded.getvalue()))
        else:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'input.dxf'
                path.write_bytes(uploaded.getvalue())
                nodes, bars = read_dxf(path, unit_scale, layers=tuple(x.strip() for x in layers.split(',') if x.strip()))
            bars = assign_stages_by_height(nodes, bars, ring_height)
            loads = []
            heights = nodes.set_index('node_id').z
            for stage, group in bars.groupby('stage'):
                if stage > 0:
                    endpoints = set(group.node_i) | set(group.node_j)
                    node = heights.loc[sorted(endpoints)].idxmax()
                    loads.append((int(stage), node, 0., 0., -installation*1000))
            model = StructureModel(nodes, bars, pd.DataFrame([
                ('DEFAULT', area*1e-4, inertia*1e-8, modulus*1e9, 7850.)], columns=PROFILES_COLS),
                detect_base_supports(nodes), pd.DataFrame(loads, columns=LOADS_COLS))
        problems = validate_model(model)
        if problems:
            raise ValueError('; '.join(problems))
        if len(model.nodes) > 250 or len(model.bars) > 500:
            raise ValueError('Interactive prototype limit: 250 nodes and 500 bars')
        with st.spinner('Analyzing construction steps…'):
            results = analyze_stages(model, int(batch))
    except Exception as error:
        # File parsers expose several exception types; show the error without results.
        st.error(f'Cannot analyze this model: {error}')
        return
    unstable = sum(not stage.result.stable for stage in results)
    columns = st.columns(3)
    columns[0].metric('Analysis steps', len(results))
    columns[1].metric('Unstable steps', unstable)
    columns[2].metric('Total bars', len(model.bars))
    st.caption('Bars in source stage 0 are initially installed. Later bars are ordered by source stage, '
               'then bar ID, and grouped by the chosen batch size. Self-weight accumulates. '
               'Installation loads apply only to source stages represented in each new group; '
               'a source-stage load repeats when that stage spans several groups.')
    step = st.slider('Construction step', 0, len(results)-1, len(results)-1) if len(results) > 1 else 0
    selected = results[step]
    if selected.result.stable:
        st.success(f'Step {step}: stable linear equilibrium · {len(selected.active_bars)} active bars')
    else:
        st.error(f'Step {step}: unstable — {selected.result.message}. Forces and displacements are unavailable.')
    left, right = st.columns(2)
    with left:
        color = st.selectbox('Color bars by', ['stress', 'force', 'utilization', 'buckling'])
    with right:
        scale = st.slider('Deformation multiplier', 0, 5000, 0, step=100)
    st.plotly_chart(figure_3d(model, selected, color, scale), width='stretch')
    metric = st.selectbox('History metric', ['max_force', 'max_stress', 'max_disp', 'max_buckling'])
    st.plotly_chart(figure_stage_history(results, metric), width='stretch')
    bars_tab, nodes_tab, input_tab = st.tabs(['Bar results', 'Displacements and reactions', 'Input model'])
    r = selected.result
    with bars_tab:
        table = pd.DataFrame({'bar_id': selected.active_bars})
        table['force_n'] = table.bar_id.map(r.axial_force_n)
        table['stress_pa'] = table.bar_id.map(r.stress_pa)
        table['buckling_ratio'] = table.bar_id.map(r.buckling_ratio) if r.buckling_ratio is not None else float('nan')
        st.dataframe(table, hide_index=True, width='stretch')
        st.caption('Utilization is |axial stress| / yield. Buckling is compression / pinned Euler load; '
                   'neither is a design-code capacity check. Unknown inertia produces no buckling ratio.')
    with nodes_tab:
        st.dataframe(r.displacements, hide_index=True, width='stretch')
        st.dataframe(r.reactions, hide_index=True, width='stretch')
    with input_tab:
        for name in ['nodes', 'bars', 'profiles', 'supports', 'loads']:
            st.write(name.title())
            st.dataframe(getattr(model, name), hide_index=True, width='stretch')
    st.download_button('Download model / Excel template', model_excel(model), 'dome-model.xlsx',
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    st.download_button('Download all stage results', results_excel(results), 'dome-stage-results.xlsx',
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
