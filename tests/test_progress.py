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
