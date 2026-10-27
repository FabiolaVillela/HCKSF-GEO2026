"""Streamlit interface for the independent rigid-frame demo."""
from __future__ import annotations

import io
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

SOURCE = Path(__file__).resolve().parents[1]
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

PROTOTYPE = Path(__file__).resolve().parents[2] / 'prototypes' / 'rigid-frame'
if str(PROTOTYPE) not in sys.path:
    sys.path.insert(0, str(PROTOTYPE))
from demo import example_model
from domecalc import Material, Section, analyze, export
from domecalc.viewer import export_viewer


@st.cache_data(show_spinner=False)
def calculate(diameter, thickness, modulus):
    return analyze(example_model(), Material(E=modulus * 1e9),
                   Section.circular(diameter / 1000, thickness / 1000))


@st.cache_data(show_spinner=False)
def download_bundle(result):
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        export(result, folder)
        export_viewer(result, folder / 'viewer.html')
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(folder.iterdir()):
                archive.write(path, path.name)
        return buffer.getvalue()


def model_figure(result, scale):
    figure = go.Figure()
    nodes = result['nodes']
    for deformed in ([False, True] if scale else [False]):
        coords = [[], [], []]
        for bar in result['elements']:
            for axis in range(3):
                coords[axis].extend([
                    nodes[index]['xyz_m'][axis]
                    + (scale * nodes[index]['displacement'][axis] if deformed else 0)
                    for index in (bar['i'], bar['j'])])
                coords[axis].append(None)
        figure.add_trace(go.Scatter3d(
            x=coords[0], y=coords[1], z=coords[2], mode='lines',
            name=f'Deformed ×{scale}' if deformed else 'Dome',
            line=dict(color='red' if deformed else '#2684ab', width=3)))
    supports = [node for node in nodes if node['fixed_dofs']]
    figure.add_trace(go.Scatter3d(
        x=[n['xyz_m'][0] for n in supports], y=[n['xyz_m'][1] for n in supports],
        z=[n['xyz_m'][2] for n in supports], mode='markers', name='Supports',
        marker=dict(size=5, symbol='diamond', color='black')))
    figure.update_layout(scene=dict(aspectmode='data', xaxis_title='X (m)',
                                   yaxis_title='Y (m)', zaxis_title='Z (m)'),
                         margin=dict(l=0, r=0, t=10, b=0), height=520)
    return figure


st.set_page_config(page_title='Steel dome analysis', layout='wide')
mode = st.sidebar.selectbox('Analysis mode', ['Construction stages (truss)', 'Completed dome (rigid frame)',
                                              'Dashboard (combined)'], key='analysis_mode')
if mode == 'Dashboard (combined)':
    from domestage.dashboard import render as render_dashboard
    render_dashboard()
    st.stop()
if mode == 'Construction stages (truss)':
    from domestage.stage_app import render
    render()
    st.stop()

st.title('Steel dome analysis')
st.caption('Rigid-frame prototype · synthetic dome · SI units')
st.warning('Demonstration only. Do not use these results to authorize construction or structural design.')
st.info('This mode analyzes the completed dome with rigid connections under self-weight. '
        'Choose Construction stages (truss) in the sidebar for the pin-jointed stage model.')
with st.sidebar:
    st.header('Circular steel tube')
    with st.form('analysis_settings'):
        diameter = st.number_input('Outside diameter (mm)', min_value=1.0, value=101.6)
        thickness = st.number_input('Wall thickness (mm)', min_value=0.1, value=3.175, format='%.3f')
        modulus = st.number_input('Elastic modulus (GPa)', min_value=1.0, value=200.0)
        submitted = st.form_submit_button('Run analysis', type='primary')
    st.caption('Steel density: 7850 kg/m³. Base translations restrained; rotations free. '
               'Linear elastic Euler–Bernoulli model; no strength or buckling checks.')

if submitted or 'frame_result' not in st.session_state:
    try:
        with st.spinner('Solving dome equilibrium…'):
            result = calculate(diameter, thickness, modulus)
        st.session_state.frame_result = result
        st.session_state.frame_settings = (diameter, thickness, modulus)
    except (ValueError, np.linalg.LinAlgError) as error:
        st.error(f'Analysis could not be completed: {error}')
        st.stop()
result = st.session_state.frame_result
settings = st.session_state.frame_settings
st.caption(f'Displayed results: diameter {settings[0]:g} mm, thickness {settings[1]:g} mm, '
           f'elastic modulus {settings[2]:g} GPa. Submit the form to apply changes.')
summary = result['summary']
for column, label, value in zip(
        st.columns(4), ['Nodes', 'Bars', 'Mass (kg)', 'Max displacement (mm)'],
        [summary['nodes'], summary['elements'], f"{summary['mass_kg']:,.1f}",
         f"{summary['max_displacement_m'] * 1000:.4f}"]):
    column.metric(label, value)
scale = st.slider('Deformation display multiplier', 0, 5000, 0, step=100)
st.plotly_chart(model_figure(result, scale), width='stretch')
bars = pd.DataFrame([
    {'bar_id': bar['id'], 'group': bar['layer'], 'length_m': bar['length_m'],
     'min_axial_kN': min(s['N_Vy_Vz_T_My_Mz'][0] for s in bar['stations']) / 1000,
     'max_axial_kN': max(s['N_Vy_Vz_T_My_Mz'][0] for s in bar['stations']) / 1000}
    for bar in result['elements']])
nodes = pd.DataFrame([
    {'node_id': node['id'], **{
        label: node[key][axis] * factor
        for key, labels, factor in [('displacement', ['ux_mm', 'uy_mm', 'uz_mm'], 1000),
                                    ('reaction', ['rx_kN', 'ry_kN', 'rz_kN'], .001)]
        for axis, label in enumerate(labels)}}
    for node in result['nodes']])
bar_tab, node_tab = st.tabs(['Bar forces', 'Displacements and reactions'])
with bar_tab:
    st.caption('Axial tension is positive. Min/max use the solver’s sampled stations.')
    st.dataframe(bars, hide_index=True, width='stretch')
with node_tab:
    st.dataframe(nodes, hide_index=True, width='stretch')
st.download_button('Download results and interactive viewer (ZIP)', download_bundle(result),
                   file_name='dome-results.zip', mime='application/zip')
st.caption('Archive includes JSON, CSV, a report, and a standalone HTML viewer.')
