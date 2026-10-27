"""Construction groups and independent equilibrium at each installation step."""
from __future__ import annotations

from numbers import Integral
from typing import List

from .schema import StageResult, StructureModel, validate_model
from .solver import solve_truss


def group_stages(model: StructureModel, bars_per_stage: int = 1) -> List[List[int]]:
    if isinstance(bars_per_stage, bool) or not isinstance(bars_per_stage, Integral) or bars_per_stage < 1:
        raise ValueError('bars_per_stage must be a positive integer')
    problems = validate_model(model)
    if problems:
        raise ValueError('; '.join(problems))
    ordered = model.bars.sort_values(['stage', 'bar_id'])
    initial = ordered.loc[ordered.stage == 0, 'bar_id'].tolist()
    pending = ordered.loc[ordered.stage > 0, 'bar_id'].tolist()
    return [initial] + [pending[i:i+bars_per_stage] for i in range(0, len(pending), bars_per_stage)]


def run_stages(model: StructureModel, bars_per_stage: int = 1) -> List[StageResult]:
    """Installation loads are transient, selected by each group's source stages.

    A source-stage load is applied in every subgroup containing bars from that
    source stage. Loads from earlier groups do not accumulate; self-weight does.
    StageResult.stage is the analysis-step number, starting at zero.
    """
    results, active = [], []
    source = model.bars.set_index('bar_id').stage
    for step, new in enumerate(group_stages(model, bars_per_stage)):
        active.extend(new)
        stages = set(source.loc[new]) if new else {0}
        loads = model.loads.loc[model.loads.stage.isin(stages)]
        results.append(StageResult(step, active.copy(), new.copy(), solve_truss(model, active, loads)))
    return results
