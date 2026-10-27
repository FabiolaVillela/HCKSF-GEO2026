"""Default model (QuickDome Ø40 m DXF) and DXF unit auto-detection."""
import pytest

from domestage.assembly import catalog, geometry_from_dxf, solve_stage, stage_plan
from domestage.default_model import DEFAULT_DXF, DEFAULT_NAME, default_geometry, default_model
from domestage.server import Handler


def get(path):
    handler = object.__new__(Handler)
    handler.path = path
    output = []
    handler.send = lambda status, result, *args: output.append((status, result))
    handler.do_GET()
    return output[0]


def test_default_model_is_the_quickdome_dxf():
    model = default_model()
    assert DEFAULT_DXF.exists() and model['file'] == DEFAULT_DXF.name and model['name'] == DEFAULT_NAME
    assert (model['nodes'], model['bars'], model['supports'], model['units']) == (109, 297, 27, 'mm')
    assert model['report']['errors'] == [] and len(model['report']['components']) == 1
    g = model['geometry']
    xs, zs = [n['x'] for n in g['nodes']], [n['z'] for n in g['nodes']]
    assert max(xs) - min(xs) == pytest.approx(39.93, abs=0.01)  # 40 m nominal diameter, in metres
    assert max(zs) - min(zs) == pytest.approx(13.333, abs=0.001)
    assert sum(b['isBase'] for b in g['bars']) == 27  # shoulder ring installed at stage 0


def test_default_geometry_is_a_copy():
    g = default_geometry()
    g['nodes'].clear()
    assert len(default_geometry()['nodes']) == 109


def test_default_model_solves_with_rigid_connections():
    g = default_geometry()
    cfg = dict(material='Acero', profile=catalog()['profiles'][2], connection='empotrada', support='empotrado',
               bars_per_step=2, worker_kg=0)
    plan = stage_plan(g, 2)
    assert len(plan) == 136
    final = solve_stage(g, cfg, len(plan) - 1)
    assert final['status'] == 'stable' and final['active_count'] == 297


def test_http_default_model_endpoint():
    status, body = get('/api/default-model')
    assert status == 200 and body['name'] == DEFAULT_NAME and len(body['geometry']['bars']) == 297


@pytest.mark.parametrize('units', [None, '', 'auto'])
def test_dxf_units_auto_detect_uses_insunits(units):
    """'auto' (the simulator's default choice) must use the units declared in the DXF."""
    geometry, report = geometry_from_dxf(DEFAULT_DXF.read_bytes(), units, 0.001)
    assert report['units'] == 'mm' and len(geometry['nodes']) == 109
