"""Near-mechanism validity check (issue #14)."""
import math

import numpy as np
import pandas as pd
import pytest

from domestage.assembly import catalog, geometry_from_structure, progress_series, solve_stage, stage_plan
from domestage.demo_model import generate_demo_dome
from domestage.schema import StructureModel
from domestage.solver import solve_truss
from domestage.validity import ROTATION_LIMIT_RAD, chord_rotations, rotation_problem


def test_chord_rotation_ignores_axial_motion_and_measures_transverse_motion():
    start, end = [[0, 0, 0], [0, 0, 0]], [[2, 0, 0], [0, 4, 0]]
    zero = [[0, 0, 0], [0, 0, 0]]
    axial = [[0.5, 0, 0], [0, 0.7, 0]]           # pure stretch: no rotation
    assert chord_rotations(start, end, zero, axial) == pytest.approx([0, 0])
    sideways = [[0, 0.2, 0], [0.2, 0, 0]]        # transverse by 0.2 over lengths 2 and 4
    assert chord_rotations(start, end, zero, sideways) == pytest.approx([0.1, 0.05])
    assert chord_rotations(start, end, sideways, zero) == pytest.approx([0.1, 0.05])  # rigid-body shift cancels


def test_rotation_problem_message_and_limit():
    assert rotation_problem(7, ROTATION_LIMIT_RAD / 2) is None
    message = rotation_problem(7, 3.0)
    assert 'bar 7' in message and 'near-mechanism' in message and 'not valid' in message
    assert rotation_problem(7, float('nan'))  # a non-finite result is never valid


def shallow_node(height):
    """One node held by four bars from supports 2 m away, at the given height, loaded downward."""
    nodes = pd.DataFrame([(1, 2., 0, 0), (2, -2., 0, 0), (3, 0, 2., 0), (4, 0, -2., 0), (5, 0, 0, height)],
                         columns=['node_id', 'x', 'y', 'z'])
    bars = pd.DataFrame([(i, i, 5, 'P', 0) for i in range(1, 5)],
                        columns=['bar_id', 'node_i', 'node_j', 'profile', 'stage'])
    profiles = pd.DataFrame([('P', 1e-3, 0., 2e11, 7850.)],
                            columns=['profile', 'area_m2', 'inertia_m4', 'E_pa', 'density_kgm3'])
    supports = pd.DataFrame([(i, True, True, True) for i in range(1, 5)],
                            columns=['node_id', 'fix_x', 'fix_y', 'fix_z'])
    loads = pd.DataFrame([(0, 5, 0., 0., -50_000.)], columns=['stage', 'node_id', 'fx_n', 'fy_n', 'fz_n'])
    return StructureModel(nodes, bars, profiles, supports, loads)


def test_solver_flags_a_shallow_node_but_not_a_normal_one():
    flat = shallow_node(0.02)                    # bars almost coplanar: ~0.6 degrees of slope
    result = solve_truss(flat, [1, 2, 3, 4], extra_loads=flat.loads, include_self_weight=False)
    assert not result.stable and 'near-mechanism' in result.message
    assert result.axial_force_n.isna().all() and result.displacements.uz.isna().all()
    tall = shallow_node(2.0)                     # same loading, ordinary geometry
    result = solve_truss(tall, [1, 2, 3, 4], extra_loads=tall.loads, include_self_weight=False)
    assert result.stable


CONFIG = dict(material='Acero', profile=catalog()['profiles'][2], bars_per_step=2)


@pytest.fixture(scope='module')
def dome():
    return geometry_from_structure(generate_demo_dome(total_height=3.2))


@pytest.mark.parametrize('worker_kg', [0, 100])
def test_demo_dome_pinned_stages_56_and_57_are_no_longer_reported_stable(dome, worker_kg):
    cfg = dict(CONFIG, connection='articulada', support='articulado', worker_kg=worker_kg)
    for stage in (56, 57):
        result = solve_stage(dome, cfg, stage)
        assert result['status'] == 'unstable' and result['stable'] is False
        assert 'near-mechanism' in result['message']
        assert result['forces'] == {} and result['max_displacement_mm'] is None
    for stage in (58, 59, 60):                   # genuine, small-rotation results are kept
        assert solve_stage(dome, cfg, stage)['status'] == 'stable'
    series = progress_series(dome, cfg)
    assert [s['max_force_kn'] for s in series if s['stage'] in (56, 57)] == [None, None]


@pytest.mark.parametrize('worker_kg', [0, 100])
def test_demo_dome_rigid_connections_are_unchanged(dome, worker_kg):
    cfg = dict(CONFIG, connection='empotrada', support='empotrado', worker_kg=worker_kg)
    stages = len(stage_plan(dome, 2))
    results = [solve_stage(dome, cfg, s) for s in range(stages)]
    assert stages == 61 and all(r['status'] == 'stable' for r in results)


def test_team_solver_agrees_on_the_demo_dome_stage_56():
    model = generate_demo_dome(total_height=3.2)
    plan = stage_plan(geometry_from_structure(model), 2)
    flagged = solve_truss(model, plan[56]['active_bar_ids'])
    assert not flagged.stable and 'near-mechanism' in flagged.message
