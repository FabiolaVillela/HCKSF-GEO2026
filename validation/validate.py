"""Validation of the truss solver against hand calculations.

Run from the repo root:  python validation/validate.py

For each case it prints: hand-calculated value, an independent NumPy reference
(dense stiffness assembly, written here, NOT the team's solver), and the team's
`domestage.solver.solve_truss` once it is implemented. Exit code 1 on any mismatch.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))

from domestage.schema import G  # noqa: E402
from test_schema import tripod_model  # noqa: E402

RTOL = 1e-6


def reference_solve(model, active, include_self_weight, use_loads=True):
    """Independent dense reference. Returns (stable, axial_force dict, apex uz)."""
    pos = model.nodes.set_index("node_id")[["x", "y", "z"]]
    prof = model.profiles.set_index("profile")
    ids = list(pos.index)
    dof = {n: 3 * i for i, n in enumerate(ids)}
    K = np.zeros((3 * len(ids),) * 2)
    f = np.zeros(3 * len(ids))
    bars = model.bars[model.bars["bar_id"].isin(active)]
    geo = {}
    for _, b in bars.iterrows():
        p, q = pos.loc[b.node_i].to_numpy(), pos.loc[b.node_j].to_numpy()
        L = np.linalg.norm(q - p)
        c = (q - p) / L
        pr = prof.loc[b.profile]
        k = pr.E_pa * pr.area_m2 / L
        blk = k * np.outer(c, c)
        a, d = dof[b.node_i], dof[b.node_j]
        K[a:a+3, a:a+3] += blk; K[d:d+3, d:d+3] += blk
        K[a:a+3, d:d+3] -= blk; K[d:d+3, a:a+3] -= blk
        geo[b.bar_id] = (a, d, c, k)
        if include_self_weight:
            w = pr.density_kgm3 * pr.area_m2 * L * G
            f[a + 2] -= w / 2; f[d + 2] -= w / 2
    if use_loads:
        for _, l in model.loads.iterrows():
            i = dof[l.node_id]
            f[i:i+3] += [l.fx_n, l.fy_n, l.fz_n]
    fixed = [dof[r.node_id] + j for _, r in model.supports.iterrows()
             for j, col in enumerate(["fix_x", "fix_y", "fix_z"]) if r[col]]
    free = [d for d in range(3 * len(ids)) if d not in fixed]
    Kff = K[np.ix_(free, free)]
    # nodes untouched by any active bar are ignored, not unstable
    touched = np.abs(K).sum(axis=1) > 0
    free = [d for d in free if touched[d]]
    Kff = K[np.ix_(free, free)]
    if np.linalg.matrix_rank(Kff) < len(free):
        return False, {}, float("nan")
    u = np.zeros(3 * len(ids))
    u[free] = np.linalg.solve(Kff, f[free])
    forces = {bid: k * float(c @ (u[d:d+3] - u[a:a+3])) for bid, (a, d, c, k) in geo.items()}
    return True, forces, u[dof[4] + 2]


def team_solve(model, active, include_self_weight, use_loads=True):
    from domestage.solver import solve_truss
    extra = model.loads if use_loads else model.loads.iloc[0:0]
    return solve_truss(model, active, extra_loads=extra, include_self_weight=include_self_weight)


def main() -> int:
    failures = 0

    def check(label, got, want, rtol=RTOL):
        nonlocal failures
        ok = math.isclose(got, want, rel_tol=rtol, abs_tol=1e-12)
        failures += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {label}: {got:.6g} (expected {want:.6g})")

    # Case A: tripod, 1000 N down, no self-weight.
    print("Case A: tripod, 1000 N at apex")
    m = tripod_model(0.0)
    want_f = -1000 * math.sqrt(2) / 3
    want_uz = -1000 * math.sqrt(2) / 3 * math.sqrt(2) / (2e11 * 1e-4) * math.sqrt(2)
    stable, forces, uz = reference_solve(m, [1, 2, 3], False)
    assert stable
    check("reference bar force [N]", forces[1], want_f)
    check("reference apex uz [m]", uz, want_uz)

    # Case B: tripod with self-weight (steel 7850 kg/m3) plus the 1000 N load.
    print("Case B: tripod, 1000 N + self-weight")
    m2 = tripod_model(7850.0)
    L = math.sqrt(2)
    p_apex = 1000 + 3 * 0.5 * 7850 * 1e-4 * L * G
    stable, forces, _ = reference_solve(m2, [1, 2, 3], True)
    check("reference bar force [N]", forces[1], -p_apex * math.sqrt(2) / 3)

    # Case C: only two bars installed -> mechanism.
    print("Case C: two bars only (mechanism)")
    stable, _, _ = reference_solve(m, [1, 2], False)
    failures += stable
    print(f"  {'PASS' if not stable else 'FAIL'}  reference flags unstable")

    # Team solver, if available.
    print("Team solver (domestage.solver.solve_truss)")
    try:
        r = team_solve(m, [1, 2, 3], False)
        check("A bar force [N]", float(r.axial_force_n.iloc[0]), want_f)
        uzs = r.displacements.loc[r.displacements["node_id"] == 4, "uz"].iloc[0]
        check("A apex uz [m]", float(uzs), want_uz, rtol=1e-3)
        r = team_solve(m2, [1, 2, 3], True)
        check("B bar force [N]", float(r.axial_force_n.iloc[0]), -p_apex * math.sqrt(2) / 3)
        r = team_solve(m, [1, 2], False)
        failures += r.stable
        print(f"  {'PASS' if not r.stable else 'FAIL'}  C flagged unstable")
    except NotImplementedError:
        print("  SKIPPED  solve_truss not implemented yet")

    print("OK" if not failures else f"{failures} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
