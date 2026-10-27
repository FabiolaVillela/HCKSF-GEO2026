"""Utilization figures by % of assembly progress (plan + elevation) for the calculation report."""
import pytest

from domestage.aisc import check_result
from domestage.assembly import solve_stage
from domestage.report_figures import UNCHECKED, build_figures, figures_html, utilization_color
from test_assembly import tetrahedron, config
from test_server import post

GRADE_C = {'grade': 'a500-21-c'}


def rigid():
    return {**config(), 'connection': 'empotrada', 'support': 'empotrado'}


def test_utilization_colour_matches_simulator_scale():
    # Same expectations as tests/test_aisc_colors.cjs for utilizationColor() in aisc-view.js.
    assert utilization_color(0) == '#00ffff' and utilization_color(.5) == '#00aaff'
    assert utilization_color(.75) == '#0000ff' and utilization_color(1) == '#000000'
    assert utilization_color(1.00000001) == '#ffff00' and utilization_color(1.1) == '#ff9900'
    assert utilization_color(1.25) == '#ff0000' and utilization_color(5) == '#ff0000'
    assert utilization_color(.875) == '#000080' and utilization_color(1.175) == '#ff4d00'
    assert utilization_color(None) == utilization_color(-1) == utilization_color(float('nan')) == UNCHECKED == '#737373'


def test_milestones_pick_first_stage_reaching_each_progress():
    # Tetrahedron, 1 bar per stage: progress 50, 66.7, 83.3, 100 %.
    data = build_figures(tetrahedron(), rigid(), GRADE_C, [50, 67, 83, 95, 100])
    assert [(f['target_pct'], f['stage'], f['progress_pct']) for f in data['figures']] == [
        (50, 0, 50), (67, 2, 83.3), (95, 3, 100)]  # 83 and 100 hit already-listed stages
    assert [len(f['active_bar_ids']) for f in data['figures']] == [3, 5, 6]
    # Pinned tetrahedron: stage 2 is a mechanism -> no utilization, but the figure is still listed.
    pinned = build_figures(tetrahedron(), config(), GRADE_C, '50, 83')
    assert [f['status'] for f in pinned['figures']] == ['stable', 'unstable']
    assert pinned['figures'][1]['utilization'] == {} and pinned['figures'][1]['max_utilization'] is None


def test_bar_utilization_matches_aisc_check():
    model, cfg = tetrahedron(), rigid()
    data = build_figures(model, cfg, GRADE_C, [100])
    figure = data['figures'][0]
    checked = check_result(solve_stage(model, cfg, figure['stage']), GRADE_C)
    assert figure['utilization'] == {m['id']: m['utilization'] for m in checked['members']}
    assert figure['max_utilization'] == pytest.approx(checked['max_utilization'])


@pytest.mark.parametrize('cfg, design, milestones', [
    ({}, {}, None),                                        # no grade
    ({'material': 'Aluminio'}, {'grade': '6061-t6'}, None),  # aluminum
    ({'worker_kg': 80}, GRADE_C, None),                    # installer load
    ({}, GRADE_C, [0]), ({}, GRADE_C, [120]), ({}, GRADE_C, 'abc'), ({}, GRADE_C, list(range(5, 70, 5))),
    ({}, {'grade': 'not-a-grade'}, None),
])
def test_invalid_inputs_raise(cfg, design, milestones):
    with pytest.raises(ValueError):
        build_figures(tetrahedron(), {**rigid(), **cfg}, design, milestones)


def test_html_document_in_spanish_and_english():
    model = tetrahedron()
    es = figures_html(build_figures(model, rigid(), GRADE_C, [50, 100], 'es'), 'Tetraedro')
    en = figures_html(build_figures(model, rigid(), GRADE_C, [50, 100], 'en'), 'Tetrahedron')
    for doc in (es, en):
        assert doc.startswith('<!DOCTYPE html>') and doc.count('<figure id=') == 4  # plan + elevation per milestone
    assert 'Armado Domo 50%' in es and 'Armado Domo 100%' in es and 'Planta' in es and 'Elevación' in es
    assert 'son menores a 1.0' in es and 'ASTM A500/A500M-21 Grado C' in es and 'Descargar PNG' in es
    assert 'Dome assembly 50%' in en and 'Plan' in en and 'Elevation' in en and 'lower than 1.0' in en
    for word in ('Armado', 'Planta', 'Elevación', 'Utilización', 'Descargar', 'empotrad'):
        assert word not in en
    with pytest.raises(ValueError):
        build_figures(model, rigid(), GRADE_C, None, 'fr')


def test_http_endpoint():
    payload = dict(geometry=tetrahedron(), config=rigid(), design=GRADE_C, milestones='50, 100', language='es',
                   model_name='Tetraedro')
    status, body = post('/api/utilization-figures', payload)
    assert status == 200 and isinstance(body, bytes)  # raw HTML, not a JSON-encoded string
    html = body.decode('utf-8')
    assert html.startswith('<!DOCTYPE html>') and 'Armado Domo 50%' in html and 'Elevación' in html and 'Tetraedro' in html
    status, body = post('/api/utilization-figures', {**payload, 'design': {}})
    assert status == 400 and 'grado de material' in body['message']
