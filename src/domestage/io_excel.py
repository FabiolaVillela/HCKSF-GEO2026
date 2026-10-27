"""Excel template reading and results export. OWNER: Role 2 (data I/O + example dome).

Depends on: schema.py only.
"""
from __future__ import annotations

from typing import List

from .schema import StageResult, StructureModel


def read_template(path: str) -> StructureModel:
    """Read the Excel template (sheets: Nodes, Bars, Profiles, Supports, Loads, Criteria).

    Column names must match schema.*_COLS. Must call schema.validate_model and raise
    ValueError with the list of problems if the model is invalid.
    """
    raise NotImplementedError


def write_template(model: StructureModel, path: str) -> None:
    """Write a model to the Excel template format (inverse of read_template)."""
    raise NotImplementedError


def export_results(results: List[StageResult], path: str) -> None:
    """Export per-stage results to Excel.

    Sheets: Summary (stage, stable, max |force|, max stress, max displacement),
    Bars (stage, bar_id, force, stress, buckling_ratio), Reactions.
    """
    raise NotImplementedError
