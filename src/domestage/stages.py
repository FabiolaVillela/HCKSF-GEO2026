"""Stage loop. OWNER: Role 4 (stages / construction logic).

Depends on: schema.py and solver.solve_truss (signature fixed in solver.py).
Until the solver is ready, develop against a fake solve_truss.
"""
from __future__ import annotations

from typing import List

from .schema import StageResult, StructureModel


def group_stages(model: StructureModel, bars_per_stage: int = 1) -> List[List[int]]:
    """Split the bars into analysis groups, following the order of `bars.stage`.

    Bars with stage == 0 are the initial structure (already installed).
    After that, every `bars_per_stage` bars (ordered by stage, then bar_id) form one
    analysis step. Returns a list of lists of bar_ids (first item = initial bars).
    """
    raise NotImplementedError


def run_stages(model: StructureModel, bars_per_stage: int = 1) -> List[StageResult]:
    """Run the analysis after each group of installed bars.

    For each step: active bars = all bars installed so far; installation load =
    model.loads for the newly installed bars' stage(s); call solver.solve_truss.
    Never raise on instability: the StageResult carries result.stable = False.
    """
    raise NotImplementedError
