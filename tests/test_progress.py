"""Series de máximos por etapa para las gráficas de avance del simulador."""
import pytest
from domestage.assembly import progress_series, solve_stage, stage_plan
from test_assembly import tetrahedron, config
from test_server import post


def test_progress_series_matches_each_stage_and_skips_mechanisms():
    model, cfg = tetrahedron(), config()
    series = progress_series(model, cfg)
    plan = stage_plan(model, cfg['bars_per_step'])
    assert [s['stage'] for s in series] == [p['stage'] for p in plan]
    assert [s['progress_pct'] for s in series] == [p['progress_pct'] for p in plan] == [50, 66.7, 83.3, 100]
    assert [s['status'] for s in series] == ['stable', 'unstable', 'unstable', 'stable']
    # Un mecanismo no tiene fuerzas ni deflexión: no se inventan valores.
    for s in series[1:3]:
        assert s['max_force_kn'] is None and s['max_displacement_mm'] is None
    final = solve_stage(model, cfg, 3)
    assert series[3]['max_tension_kn'] == pytest.approx(final['max_tension_kn'])
    assert series[3]['max_compression_kn'] == pytest.approx(final['max_compression_kn'])
    assert series[3]['max_force_kn'] == pytest.approx(max(final['max_tension_kn'], final['max_compression_kn']))
    assert series[3]['max_displacement_mm'] == pytest.approx(final['max_displacement_mm'])
    assert series[3]['max_displacement_mm'] > 0


def test_progress_series_follows_configuration():
    model = tetrahedron()
    pinned = progress_series(model, {**config(), 'connection': 'articulada'})
    rigid = progress_series(model, {**config(), 'connection': 'empotrada'})
    assert [s['status'] for s in rigid].count('stable') >= [s['status'] for s in pinned].count('stable')
    assert len(progress_series(model, {**config(), 'bars_per_step': 3})) == 2


def test_http_progress_endpoint():
    status, result = post('/api/progress', dict(geometry=tetrahedron(), config=config()))
    assert status == 200 and len(result) == 4
    assert result[-1]['status'] == 'stable'
    assert post('/api/progress', dict(config=config()))[0] == 400


def test_progress_series_utilization_matches_aisc_check_per_stage():
    from domestage.aisc import check_all_stages
    model = tetrahedron()
    cfg = {**config(), 'connection': 'empotrada', 'support': 'empotrado'}
    design = {'grade': 'a500-21-c'}
    series = progress_series(model, cfg, design)
    checks = check_all_stages(model, cfg, design)
    assert len(series) == len(checks)
    for s, c in zip(series, checks):
        assert s['utilization_status'] == 'aisc'
        if s['status'] == 'stable':
            assert s['max_utilization'] == pytest.approx(c['max_utilization'])
            assert s['governing_bar'] == c['governing']['member_id']
            assert s['governing_equation'] == c['governing']['equation']
        else:
            assert s['max_utilization'] is None


def test_progress_series_utilization_not_computed_without_valid_inputs():
    model = tetrahedron()
    assert {s['utilization_status'] for s in progress_series(model, config())} == {'no_grade'}
    assert all(s['max_utilization'] is None for s in progress_series(model, config()))
    alu = progress_series(model, {**config(), 'material': 'Aluminio'}, {'grade': '6061-t6'})
    assert {s['utilization_status'] for s in alu} == {'aluminum'}
    worker = progress_series(model, {**config(), 'worker_kg': 80}, {'grade': 'a500-21-c'})
    assert {s['utilization_status'] for s in worker} == {'installer'}
    with pytest.raises(ValueError):
        progress_series(model, config(), {'grade': 'not-a-grade'})


def test_http_progress_endpoint_with_design():
    payload = dict(geometry=tetrahedron(), config={**config(), 'connection': 'empotrada'}, design={'grade': 'a500-21-c'})
    status, result = post('/api/progress', payload)
    assert status == 200 and result[-1]['max_utilization'] is not None
    assert post('/api/progress', {**payload, 'design': {'grade': 'not-a-grade'}})[0] == 400
