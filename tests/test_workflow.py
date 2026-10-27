import io
import numpy as np
import pandas as pd
import pytest
from domestage.demo import generate_dome
from domestage.io_excel import write_template, read_template, export_results
from domestage.schema import validate_model
from domestage.stages import group_stages, run_stages
from domestage.viz import figure_3d, figure_stage_history
from test_schema import tripod_model


def test_dome_stage_workflow_and_export():
    model = generate_dome()
    assert validate_model(model) == []
    assert (len(model.nodes), len(model.bars)) == (25, 64)
    groups = group_stages(model, 8)
    assert len(groups[0]) == 8
    assert len({bar for group in groups for bar in group}) == 64
    results = run_stages(model, 8)
    assert results[0].result.stable
    assert any(not s.result.stable for s in results)
    assert results[-1].result.stable
    assert results[-1].active_bars == sum(groups, [])
    final = results[-1].result
    assert final.axial_force_n.notna().all()
    # All generated bars share a profile. Verify applied vertical loads balance.
    nodes = model.nodes.set_index('node_id')[['x', 'y', 'z']]
    length = sum(np.linalg.norm(nodes.loc[b.node_j] - nodes.loc[b.node_i]) for b in model.bars.itertuples())
    assert final.reactions.rz.sum() == pytest.approx(length * 5e-4 * 7850 * 9.81 + 1000)
    for color in ['force', 'stress', 'utilization', 'buckling']:
        assert len(figure_3d(model, results[-1], color, 100).data) > len(model.bars)
    unstable = next(s for s in results if not s.result.stable)
    assert 'UNSTABLE' in figure_3d(model, unstable).layout.title.text
    for metric in ['max_force', 'max_stress', 'max_disp', 'max_buckling']:
        fig = figure_stage_history(results, metric)
        assert fig.data[0].y[unstable.stage] is None
        assert unstable.stage in fig.data[1].x
    out = io.BytesIO()
    export_results(results, out)
    tables = pd.read_excel(io.BytesIO(out.getvalue()), sheet_name=None)
    assert set(tables) == {'Summary', 'Bars', 'Reactions', 'Displacements'}
    assert len(tables['Summary']) == len(results)
    bad = tables['Bars'].loc[tables['Bars'].stage == unstable.stage]
    assert bad.force_n.isna().all()


def test_excel_round_trip_and_invalid_model():
    model = generate_dome()
    output = io.BytesIO()
    write_template(model, output)
    restored = read_template(io.BytesIO(output.getvalue()))
    for name in ['nodes', 'bars', 'profiles', 'supports', 'loads']:
        pd.testing.assert_frame_equal(getattr(restored, name), getattr(model, name), check_dtype=False)
    assert restored.criteria == model.criteria
    with pytest.raises(ValueError, match='Missing sheets'):
        source = io.BytesIO()
        pd.DataFrame({'x': [1]}).to_excel(source, index=False)
        read_template(io.BytesIO(source.getvalue()))
    model.profiles.loc[0, 'area_m2'] = -1
    with pytest.raises(ValueError, match='positive'):
        write_template(model, io.BytesIO())


def test_grouping_and_transient_installation_loads():
    model = tripod_model()
    model.bars.stage = [0, 1, 2]
    model.loads.stage = 2
    assert group_stages(model, 1) == [[1], [2], [3]]
    results = run_stages(model)
    assert not results[0].result.stable
    assert not results[1].result.stable
    assert results[2].result.stable
    assert results[2].result.reactions.rz.sum() == pytest.approx(1000.)
    # Once the original load's source stage has passed, it must not persist.
    model.bars.stage = 0
    model.nodes.loc[len(model.nodes)] = [5, 0., 0., -1.]
    model.supports.loc[len(model.supports)] = [5, True, True, True]
    model.bars.loc[len(model.bars)] = [4, 1, 5, 'P', 1]
    model.loads.stage = 0
    later = run_stages(model)[-1]
    assert later.result.stable
    assert np.allclose(later.result.axial_force_n, 0)
    for invalid in [0, -1, 1.5, True]:
        with pytest.raises(ValueError):
            group_stages(model, invalid)


@pytest.mark.parametrize('column,value', [('E_pa', 0), ('density_kgm3', -1), ('inertia_m4', -1), ('area_m2', np.nan)])
def test_invalid_properties(column, value):
    model = tripod_model()
    model.profiles.loc[0, column] = value
    assert validate_model(model)
