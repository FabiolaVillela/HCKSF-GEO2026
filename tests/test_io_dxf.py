from pathlib import Path

import ezdxf
import pandas as pd
import pytest
from domestage.io_dxf import read_dxf, assign_stages_by_height, detect_base_supports
from domestage.schema import LOADS_COLS, PROFILES_COLS, StructureModel, validate_model
from domestage.solver import solve_truss


def test_line_polyline_units_merging_and_stages(tmp_path):
    doc = ezdxf.new()
    space = doc.modelspace()
    space.add_line((0, 0, 0), (1000, 0, 0))
    space.add_polyline3d([(1000.1, 0, 0), (1000, 0, 1000), (0, 0, 0)])
    path = tmp_path / 'wire.dxf'
    doc.saveas(path)
    nodes, bars = read_dxf(path, unit_scale=.001, tol=.001)
    assert len(nodes) == 3 and len(bars) == 3
    assert nodes.x.max() == pytest.approx(1.)
    assert bars.profile.tolist() == ['DEFAULT'] * 3
    staged = assign_stages_by_height(nodes, bars, .5)
    assert staged.stage.tolist() == [0, 1, 1]
    assert bars.stage.tolist() == [0, 0, 0]  # Assignment must not mutate input.
    supports = detect_base_supports(nodes)
    assert set(supports.node_id) == {1, 2}
    assert supports[['fix_x', 'fix_y', 'fix_z']].all().all()


def test_closed_lightweight_polyline_and_layer_filter(tmp_path):
    doc = ezdxf.new()
    doc.layers.new('wire')
    doc.modelspace().add_lwpolyline([(0, 0), (1, 0), (0, 1)], close=True, dxfattribs={'layer': 'wire'})
    doc.modelspace().add_circle((0, 0), 2)
    path = tmp_path / 'wire.dxf'
    doc.saveas(path)
    nodes, bars = read_dxf(path, layers=('wire',))
    assert len(nodes) == 3 and len(bars) == 3
    with pytest.raises(ValueError, match='Unsupported'):
        read_dxf(path)


@pytest.mark.parametrize('failure', ['duplicate', 'disconnected', 'zero', 'curve'])
def test_bad_geometry_is_rejected(tmp_path, failure):
    doc = ezdxf.new()
    space = doc.modelspace()
    space.add_line((0, 0, 0), (1, 0, 0))
    if failure == 'duplicate':
        space.add_line((1, 0, 0), (0, 0, 0))
    elif failure == 'disconnected':
        space.add_line((10, 0, 0), (11, 0, 0))
    elif failure == 'zero':
        space.add_line((1, 0, 0), (1.00001, 0, 0))
    else:
        space.add_lwpolyline([(0, 0, 1), (1, 0, 0)], format='xyb')
    path = tmp_path / 'invalid.dxf'
    doc.saveas(path)
    with pytest.raises(ValueError):
        read_dxf(path)


DEMO_DXF = Path(__file__).resolve().parents[1] / 'prototypes' / 'rigid-frame' / 'examples' / 'demo-dome.dxf'


def test_demo_dome_dxf_imports_as_a_valid_model():
    nodes, bars = read_dxf(DEMO_DXF)
    assert (len(nodes), len(bars)) == (49, 128)
    staged = assign_stages_by_height(nodes, bars, 1.0)
    supports = detect_base_supports(nodes)
    assert len(supports) == 16 and nodes.set_index('node_id').loc[supports.node_id, 'z'].eq(0).all()
    profiles = pd.DataFrame([('DEFAULT', 1e-3, 1e-6, 200e9, 7850.)], columns=PROFILES_COLS)
    loads = pd.DataFrame([(1, 1, 0., 0., -1000.)], columns=LOADS_COLS)
    loads['stage'] = int(staged.stage[staged.stage > 0].min())
    model = StructureModel(nodes, staged, profiles, supports, loads)
    assert validate_model(model) == []
    # Source stages are not contiguous (0, 2, 4, 5, 7); the model must still solve.
    assert sorted(set(staged.stage)) == [0, 2, 4, 5, 7]
    result = solve_truss(model, list(staged.bar_id), extra_loads=model.loads)
    assert result.stable and len(result.axial_force_n) == 128


def test_layers_filter_selects_only_listed_layers(tmp_path):
    doc = ezdxf.new()
    doc.layers.new('keep')
    doc.layers.new('drop')
    space = doc.modelspace()
    space.add_line((0, 0, 0), (1, 0, 0), dxfattribs={'layer': 'keep'})
    space.add_line((1, 0, 0), (1, 1, 0), dxfattribs={'layer': 'drop'})
    path = tmp_path / 'layers.dxf'
    doc.saveas(path)
    nodes, bars = read_dxf(path, layers=('keep',))
    assert len(bars) == 1 and len(nodes) == 2
    assert len(read_dxf(path)[1]) == 2


def test_bad_unit_scale_is_rejected():
    for bad in (0, -1, float('nan'), float('inf')):
        with pytest.raises(ValueError):
            read_dxf(DEMO_DXF, unit_scale=bad)
