import ezdxf
import pytest
from domestage.io_dxf import read_dxf, assign_stages_by_height, detect_base_supports


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
