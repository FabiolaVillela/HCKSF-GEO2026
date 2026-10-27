"""Excel template round trip, input errors and results export."""
import pandas as pd
import pytest

from domestage.demo_model import generate_demo_dome
from domestage.io_excel import export_results, read_template, write_template
from domestage.schema import StageResult
from domestage.solver import solve_truss


def staged_results(model):
    """One StageResult per source stage, built with the solver (independent of stages.py)."""
    results, active = [], []
    for stage in sorted(model.bars.stage.unique()):
        new = model.bars.loc[model.bars.stage == stage, 'bar_id'].tolist()
        active += new
        loads = model.loads.loc[model.loads.stage == stage]
        results.append(StageResult(int(stage), active.copy(), new, solve_truss(model, active, loads)))
    return results


def write_variant(path, source, drop_sheet=None, drop_column=None):
    sheets = pd.read_excel(source, sheet_name=None)
    sheets.pop(drop_sheet, None)
    if drop_column:
        sheet, column = drop_column
        sheets[sheet] = sheets[sheet].drop(columns=[column])
    with pd.ExcelWriter(path) as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)


def test_template_round_trip(tmp_path):
    model = generate_demo_dome()
    path = tmp_path / 'model.xlsx'
    write_template(model, path)
    assert pd.ExcelFile(path).sheet_names == ['Nodes', 'Bars', 'Profiles', 'Supports', 'Loads', 'Criteria']
    back = read_template(path)
    for name in ['nodes', 'bars', 'profiles', 'supports', 'loads']:
        pd.testing.assert_frame_equal(getattr(back, name).reset_index(drop=True),
                                      getattr(model, name).reset_index(drop=True), check_dtype=False)
    assert back.criteria == pytest.approx(model.criteria)


def test_missing_sheet_and_column_are_reported(tmp_path):
    path = tmp_path / 'model.xlsx'
    write_template(generate_demo_dome(), path)
    write_variant(tmp_path / 'no_loads.xlsx', path, drop_sheet='Loads')
    with pytest.raises(ValueError, match='Missing sheets'):
        read_template(tmp_path / 'no_loads.xlsx')
    write_variant(tmp_path / 'no_stage.xlsx', path, drop_column=('Bars', 'stage'))
    with pytest.raises(ValueError, match='missing columns'):
        read_template(tmp_path / 'no_stage.xlsx')


def test_invalid_model_is_not_written(tmp_path):
    model = generate_demo_dome()
    model.bars.loc[0, 'node_j'] = 9999
    with pytest.raises(ValueError):
        write_template(model, tmp_path / 'bad.xlsx')


def test_export_results_sheets(tmp_path):
    results = staged_results(generate_demo_dome())
    path = tmp_path / 'results.xlsx'
    export_results(results, path)
    sheets = pd.read_excel(path, sheet_name=None)
    assert list(sheets) == ['Summary', 'Bars', 'Reactions', 'Displacements']
    summary = sheets['Summary']
    assert summary.stage.tolist() == [r.stage for r in results]
    assert summary.stable.tolist() == [r.result.stable for r in results]
    assert len(sheets['Bars']) == sum(len(r.active_bars) for r in results)
    assert set(sheets['Reactions'].stage) == {r.stage for r in results}


def test_unstable_stage_is_exported_as_a_result_not_an_error(tmp_path):
    model = generate_demo_dome()
    fixed = set(model.supports.node_id)
    # One bar with a single supported end leaves its free node able to swing: a mechanism.
    bar = model.bars[model.bars.node_i.isin(fixed) ^ model.bars.node_j.isin(fixed)].bar_id.iloc[0]
    mechanism = StageResult(0, [int(bar)], [int(bar)], solve_truss(model, [int(bar)]))
    assert not mechanism.result.stable
    path = tmp_path / 'unstable.xlsx'
    export_results([mechanism], path)
    summary = pd.read_excel(path, sheet_name='Summary')
    assert not summary.stable[0] and pd.isna(summary.max_force_n[0]) and summary.message[0]


def test_example_script_writes_a_readable_template(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / 'examples' / 'generate_dome.py'
    out = tmp_path / 'dome.xlsx'
    done = subprocess.run([sys.executable, str(script), '--rings', '3', '--sides', '8', '--out', str(out)],
                          capture_output=True, text=True, check=True)
    assert 'Wrote' in done.stdout
    model = read_template(out)
    assert len(model.bars) > 0 and len(model.supports) > 0
