import math

import pytest

from domestage.solver import solve_truss
from test_schema import tripod_model


def test_tripod_hand_calculation():
    m = tripod_model(density=0.0)
    res = solve_truss(m, active_bar_ids=[1, 2, 3], extra_loads=m.loads, include_self_weight=False)
    assert res.stable
    expected = -1000 * math.sqrt(2) / 3
    for f in res.axial_force_n:
        assert f == pytest.approx(expected, rel=1e-6)
    uz = res.displacements.loc[res.displacements["node_id"] == 4, "uz"].iloc[0]
    assert uz == pytest.approx(-4.714e-5, rel=1e-3)


def test_two_bars_is_unstable():
    m = tripod_model()
    res = solve_truss(m, active_bar_ids=[1, 2], extra_loads=m.loads, include_self_weight=False)
    assert not res.stable


def test_self_weight_equilibrium_and_inactive_bars():
    import numpy as np
    import pandas as pd
    from domestage.schema import G
    m = tripod_model(density=7850.)
    # An uninstalled, disconnected node and bar contribute no weight or stiffness.
    m.nodes.loc[len(m.nodes)] = [99, 8., 0., 0.]
    m.bars.loc[len(m.bars)] = [99, 1, 99, 'P', 1]
    r = solve_truss(m, [1, 2, 3], m.loads)
    assert r.stable
    assert 99 not in set(r.displacements.node_id)
    expected_weight = 3 * math.sqrt(2) * 1e-4 * 7850 * G
    assert r.reactions.rz.sum() == pytest.approx(1000 + expected_weight)
    assert r.reactions.rx.sum() == pytest.approx(0, abs=1e-9)
    assert r.reactions.ry.sum() == pytest.approx(0, abs=1e-9)
    unloaded = solve_truss(m, [1, 2, 3], include_self_weight=False)
    assert unloaded.stable
    assert np.allclose(unloaded.axial_force_n, 0)
    inactive = pd.DataFrame([(99, 0., 0., -1.)], columns=['node_id', 'fx_n', 'fy_n', 'fz_n'])
    assert not solve_truss(m, [1, 2, 3], inactive).stable


def test_axial_member_and_euler_ratio():
    import pandas as pd
    from domestage.schema import StructureModel, NODES_COLS, BARS_COLS, PROFILES_COLS, SUPPORTS_COLS, LOADS_COLS
    m = StructureModel(
        pd.DataFrame([(1, 0., 0., 0.), (2, 2., 0., 0.)], columns=NODES_COLS),
        pd.DataFrame([(1, 1, 2, 'P', 0)], columns=BARS_COLS),
        pd.DataFrame([('P', .001, 1e-6, 200e9, 0.)], columns=PROFILES_COLS),
        pd.DataFrame([(1, True, True, True), (2, False, True, True)], columns=SUPPORTS_COLS),
        pd.DataFrame([(0, 2, -1000., 0., 0.)], columns=LOADS_COLS))
    r = solve_truss(m, [1], m.loads, False)
    assert r.stable
    assert r.axial_force_n[1] == pytest.approx(-1000.)
    assert r.stress_pa[1] == pytest.approx(-1e6)
    assert r.displacements.set_index('node_id').loc[2, 'ux'] == pytest.approx(-1e-5)
    assert r.buckling_ratio[1] == pytest.approx(1000 / (math.pi**2 * 200e9 * 1e-6 / 4))
    m.loads.fx_n = 1000.
    tension = solve_truss(m, [1], m.loads, False)
    assert tension.axial_force_n[1] == pytest.approx(1000.)
    assert tension.buckling_ratio[1] == 0


def test_free_structure_and_invalid_input():
    m = tripod_model()
    m.supports[['fix_x', 'fix_y', 'fix_z']] = False
    assert not solve_truss(m, [1, 2, 3]).stable
    m = tripod_model()
    with pytest.raises(ValueError, match='Active bar'):
        solve_truss(m, [999])
    m.nodes.loc[m.nodes.node_id == 4, ['x', 'y', 'z']] = [1., 0., 0.]
    with pytest.raises(ValueError, match='zero length'):
        solve_truss(m, [1, 2, 3])
