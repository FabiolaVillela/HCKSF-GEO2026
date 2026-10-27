# Contributing

Team of 4–6 people. Each role owns **different files**, so there are no merge conflicts.
Modules talk to each other only through the data contract in `src/domestage/schema.py`.

## Roles and file ownership

| Role | Owns | Depends on | Can start with |
|---|---|---|---|
| 0. Lead / integration | `schema.py`, `README.md`, `CONTRIBUTING.md`, PR reviews | – | – |
| 1. DXF / geometry | `io_dxf.py` | `schema` | the real DXF |
| 2. Data I/O + example dome | `io_excel.py`, `examples/generate_dome.py` | `schema` | `tests/test_schema.py` tripod |
| 3. Solver | `solver.py`, `tests/test_solver.py` | `schema` | the tripod hand calculation |
| 4. Stages | `stages.py` | `schema`, `solver` signature | a fake solver |
| 5. Visualization | `viz.py` | `schema` | fake `StageResult` data |
| 6. App / demo | `app.py`, demo script and slides | all, via signatures | fake data |

With 4 people: merge 0+6, 1+2, keep 3+4 and 5 separate (or 3, 4+0, 5+6, 1+2).
With 5 people: merge 0 into whoever is the most senior.

## Rules

1. **Never push to `main`.** Use one branch per role (`feature/solver`, `feature/dxf`, ...) and open a pull request.
2. **Only edit your own files.** If you need to change another module or `schema.py`, open an issue or ask the owner first.
3. **Do not change function signatures** or `schema.py` columns without telling everyone.
4. **Units:** meters, newtons, pascals, kilograms everywhere. Convert only when reading files. Z is up, gravity is -z.
5. **Tension is positive**, compression is negative.
6. **Instability is a result, not an error:** return `stable=False`, never crash.
7. Commit small and often. Pull from `main` before starting each work block.

## Data contract (summary)

| Table | Columns |
|---|---|
| nodes | `node_id, x, y, z` |
| bars | `bar_id, node_i, node_j, profile, stage` |
| profiles | `profile, area_m2, inertia_m4, E_pa, density_kgm3` |
| supports | `node_id, fix_x, fix_y, fix_z` |
| loads | `stage, node_id, fx_n, fy_n, fz_n` |

`stage == 0` means the bar is already installed at the start.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                                  # solver tests are xfail until implemented
streamlit run src/domestage/app.py
```

## Integration order

1. Roles 1, 2, 3, 5 start in parallel (no dependencies between them).
2. Role 4 starts with a fake solver and switches to the real one when the tripod test passes.
3. Role 6 builds the UI with fake data, then connects the real modules.
4. Last hour: integration on a real example dome and demo preparation. Role 0 merges.
