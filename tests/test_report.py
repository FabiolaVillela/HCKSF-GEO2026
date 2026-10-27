"""Results report: per-bar envelope + AISC member checks, per-node deflection + support type."""
import io

import numpy as np
import pandas as pd
import pytest

from domestage.aisc import check_all_stages
from domestage.assembly import solve_stage
from domestage.report import build_report, report_xlsx
from test_assembly import tetrahedron, config
from test_server import post

GRADE_C = {'grade': 'a500-21-c'}


def test_bar_envelope_matches_stage_results_and_skips_mechanisms():
    model, cfg = tetrahedron(), config()  # pinned: stages 1 and 2 are mechanisms
    report = build_report(model, cfg)
    assert [s['status'] for s in report['stages']] == ['stable', 'unstable', 'unstable', 'stable']
    assert report['summary']['stages_without_solution'] == [1, 2]
    bars = {b['bar_id']: b for b in report['bars']}
    assert [bars[b]['installed_stage'] for b in (101, 102, 103, 201, 202, 203)] == [0, 0, 0, 1, 2, 3]
    final = solve_stage(model, cfg, 3)
    for e in final['elements']:
        if e['id'] >= 201:  # inclined bars only carry load in the last (stable) stage
            axial = [s['N_Vy_Vz_T_My_Mz'][0] for s in e['stations']]
            assert bars[e['id']]['max_compression_kN'] == pytest.approx(max(0, -min(axial)) / 1000)
            assert bars[e['id']]['compression_stage'] == 3


def test_without_grade_bars_are_not_checked():
    report = build_report(tetrahedron(), config())
    assert report['summary']['checks_mode'] == 'no_grade' and report['summary']['grade'] is None
    assert all(b['check_status'] == 'not_checked' and b['max_utilization'] is None for b in report['bars'])


def test_aisc_utilization_is_the_envelope_of_check_result_over_stages():
    model, cfg = tetrahedron(), {**config(), 'connection': 'empotrada', 'support': 'empotrado'}
    report = build_report(model, cfg, GRADE_C)
    assert report['summary']['checks_mode'] == 'aisc' and report['summary']['grade']['Fy_MPa'] == 345
    expected = {}
    for stage in check_all_stages(model, cfg, GRADE_C):
        for m in stage['members']:
            if m['utilization'] is not None and m['utilization'] > expected.get(m['id'], (-1,))[0]:
                expected[m['id']] = (m['utilization'], m['equation'], m['limit_state'], stage['stage'])
    bars = {b['bar_id']: b for b in report['bars']}
    assert set(expected) == set(bars)
    for bid, (u, equation, state, stage) in expected.items():
        b = bars[bid]
        assert b['max_utilization'] == pytest.approx(u)
        assert (b['governing_check'], b['limit_state'], b['utilization_stage']) == (equation, state, stage)
        assert b['check_status'] == ('within' if u <= 1 else 'exceeds')
    assert report['summary']['max_utilization'] == pytest.approx(max(u for u, *_ in expected.values()))
    stage_rows = [s for s in report['stages'] if s['status'] == 'stable']
    assert all(s['max_utilization'] is not None for s in stage_rows)


def test_aluminum_installer_load_and_invalid_grade():
    model = tetrahedron()
    alu = build_report(model, {**config(), 'material': 'Aluminio'}, {'grade': '6061-t6'})
    assert alu['summary']['checks_mode'] == 'aluminum'
    assert {b['check_status'] for b in alu['bars']} == {'not_applicable'}
    worker = build_report(model, {**config(), 'worker_kg': 80}, GRADE_C)
    assert worker['summary']['checks_mode'] == 'installer'
    assert {b['check_status'] for b in worker['bars']} == {'not_checked'}
    with pytest.raises(ValueError):
        build_report(model, config(), {'grade': 'not-a-grade'})
    with pytest.raises(ValueError):
        build_report(model, config(), {'grade': 'custom', 'Fy_MPa': 345, 'Fu_MPa': 425})  # source required


def test_node_deflection_and_support_types():
    model = tetrahedron()
    cfg = {**config(), 'support': 'articulado', 'support_overrides': {'20': 'empotrado'}}
    report = build_report(model, cfg)
    nodes = {n['node_id']: n for n in report['nodes']}
    assert [nodes[n]['support_type'] for n in (10, 20, 30, 90)] == ['articulado', 'empotrado', 'articulado', 'free']
    final = solve_stage(model, cfg, 3)
    apex = next(d for d in final['displacements'] if d['node_id'] == 90)
    assert nodes[90]['max_deflection_mm'] == pytest.approx(np.linalg.norm(apex['values'][:3]) * 1000)
    assert nodes[90]['uz_mm'] < 0 and nodes[90]['deflection_stage'] == 3


def _workbook(report, language):
    return pd.read_excel(io.BytesIO(report_xlsx(report, language)), sheet_name=None)


def test_excel_workbook_in_english_and_spanish():
    model = tetrahedron()
    cfg = {**config(), 'support_overrides': {'20': 'empotrado'}}
    report = build_report(model, cfg, GRADE_C)
    en, es = _workbook(report, 'en'), _workbook(report, 'es')
    assert list(en) == ['Summary', 'Bars', 'Nodes', 'Stages']
    assert list(es) == ['Resumen', 'Barras', 'Nodos', 'Etapas']
    assert {'Max tension (kN)', 'Max compression (kN)', 'Max utilization', 'Governing check (AISC 360-22)',
            'Limit state', 'Member check'} <= set(en['Bars'])
    assert {'Tracción máx. (kN)', 'Compresión máx. (kN)', 'Utilización máx.', 'Revisión que rige (AISC 360-22)',
            'Estado límite', 'Revisión del elemento'} <= set(es['Barras'])
    assert set(en['Bars']['Member check']) <= {'Within included checks (≤ 1)', 'Exceeds (> 1)', 'Unavailable'}
    assert set(es['Barras']['Revisión del elemento']) <= {'Dentro de las revisiones incluidas (≤ 1)', 'Excede (> 1)', 'No disponible'}
    assert set(en['Bars']['Limit state'].dropna()) <= {'Tension', 'Compression', 'Flexure + tension', 'Flexure + compression',
                                                       'Biaxial flexure (conservative sum)'}
    assert set(es['Barras']['Estado límite'].dropna()) <= {'Tracción', 'Compresión', 'Flexotracción', 'Flexocompresión',
                                                          'Flexión biaxial (suma conservadora)'}
    assert set(en['Nodes']['Support type']) == {'Pinned', 'Fixed', 'Free'}
    assert set(es['Nodos']['Tipo de apoyo']) == {'Articulado', 'Empotrado', 'Libre'}
    assert set(en['Stages']['Status']) == {'Solved', 'Mechanism (no solution)'}
    assert set(es['Etapas']['Estado']) == {'Resuelta', 'Mecanismo (sin solución)'}
    assert 'Linear elastic equilibrium calculated.' in set(en['Stages']['Engine message'])
    assert 'Equilibrio elástico lineal calculado.' in set(es['Etapas']['Mensaje del motor'])
    summary_en = dict(zip(en['Summary']['Item'], en['Summary']['Value']))
    summary_es = dict(zip(es['Resumen']['Concepto'], es['Resumen']['Valor']))
    assert summary_en['Material'] == 'Steel' and summary_es['Material'] == 'Acero'
    assert summary_en['Material grade'] == 'ASTM A500/A500M-21 Grade C'
    assert summary_es['Grado de material'] == 'ASTM A500/A500M-21 Grado C'
    assert 'AISC 360-22' in summary_en['Member checks'] and 'AISC 360-22' in summary_es['Revisiones de elementos']
    assert 'node-to-node' in summary_en['Design basis'] and 'entre nodos' in summary_es['Bases de diseño']
    with pytest.raises(ValueError):
        report_xlsx(report, 'fr')


def test_excel_without_grade_says_not_checked():
    report = build_report(tetrahedron(), config())
    en, es = _workbook(report, 'en'), _workbook(report, 'es')
    assert set(en['Bars']['Member check']) == {'Not checked'}
    assert set(es['Barras']['Revisión del elemento']) == {'Sin revisar'}
    assert 'Not checked' in dict(zip(en['Summary']['Item'], en['Summary']['Value']))['Member checks']
    assert 'Sin revisar' in dict(zip(es['Resumen']['Concepto'], es['Resumen']['Valor']))['Revisiones de elementos']
    assert 'Max utilization' not in en['Stages'] and 'Utilización máx.' not in es['Etapas']


def test_http_report_endpoint_uses_language_and_design():
    model, cfg = tetrahedron(), config()
    for language, first_sheet, util in (('en', 'Summary', 'Max utilization'), ('es', 'Resumen', 'Utilización máx.')):
        status, body = post('/api/report', dict(geometry=model, config=cfg, design=GRADE_C, language=language))
        assert status == 200 and body[:2] == b'PK'  # xlsx is a zip file
        sheets = pd.read_excel(io.BytesIO(body), sheet_name=None)
        assert list(sheets)[0] == first_sheet
        assert sheets[list(sheets)[1]][util].notna().any()
    status, body = post('/api/report', dict(geometry=model, config=cfg))  # no design, default English
    assert status == 200 and list(pd.read_excel(io.BytesIO(body), sheet_name=None))[0] == 'Summary'
    assert post('/api/report', dict(config=cfg))[0] == 400
    assert post('/api/report', dict(geometry=model, config=cfg, language='fr'))[0] == 400
    assert post('/api/report', dict(geometry=model, config=cfg, design={'grade': 'not-a-grade'}))[0] == 400
