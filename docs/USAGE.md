# Run the dome analysis app

From the repository root, using Python 3.10 or newer:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r prototypes/rigid-frame/requirements.txt
.venv/bin/python -m streamlit run src/domestage/app.py
```

On your own computer, open the address printed by Streamlit. In a cloud workspace,
use the host's supported application access or deploy the app separately. Publishing
an environment saves development tools and files; it does not host the app publicly.

## Construction stages (default)

The default synthetic dome runs without uploading a file. Choose the number of bars
installed per analysis step and use **Construction step** to inspect each assembly.
Bars already assigned source stage 0 form the initial structure. Remaining bars are
ordered by source stage then bar ID and installed in batches. Analysis-step numbers
are separate from the input model's source-stage labels.

Each step solves a fresh, linear 3D pin-jointed truss equilibrium. Installed bars
contribute stiffness and accumulated self-weight. Uninstalled nodes are ignored unless
a nonzero load is applied to one, which makes that step unavailable. Installation
loads are transient: the loads matching the source stages of newly installed bars
apply to the current step. A load repeats if its source stage spans several batches;
loads from earlier source stages do not accumulate. The synthetic example applies
one downward 1 kN load per source stage at a node on the new ring (or the apex).

An unstable or ill-conditioned step displays a warning and NaN results. An unloaded
mechanism is still unstable. An initially restrained base ring has zero displacement
and is a valid fully restrained state. The completed default dome is stable; several
partial assemblies are mechanisms. Changing batch size changes the intermediate
structures and may change which mechanisms are encountered.

The 3D plot shows inactive bars in gray, supports, forces or stresses, and optional
magnified displacements. Utilization is absolute axial stress divided by yield
stress. The Euler ratio uses pinned ends and the supplied second moment of area;
missing inertia (zero) means the ratio is unavailable. Neither indicator is a
code-based strength or buckling design check. History gaps and red crosses identify
unstable steps; crosses at zero are status markers, not zero-force solutions.

Download **model / Excel template** to inspect or edit the input. Download **all
stage results** for Summary, Bars, Reactions and Displacements sheets. Internal and
exported units are m, N, Pa, kg. Tension is positive, compression negative; Z is up.

## Excel input

Select **Excel template** and upload an `.xlsx` with these exact sheets and columns:

| Sheet | Columns |
| --- | --- |
| Nodes | node_id, x, y, z |
| Bars | bar_id, node_i, node_j, profile, stage |
| Profiles | profile, area_m2, inertia_m4, E_pa, density_kgm3 |
| Supports | node_id, fix_x, fix_y, fix_z |
| Loads | stage, node_id, fx_n, fy_n, fz_n |
| Criteria | name, value (include a positive yield_pa row) |

IDs and stage labels are integers; stages are nonnegative. Restraints accept
true/false or 0/1. Loads may be an empty table with headers. Profiles require
positive area and elastic modulus and nonnegative inertia and density. Names and
references must match. The reader validates input before running the solver.

Generate the example without opening Streamlit:

```bash
.venv/bin/python examples/generate_dome.py --rings 3 --sides 8 --out data/example_dome.xlsx
```

## DXF input

Select **DXF wireframe** and explicitly set meters per drawing unit (0.001 for mm).
The importer reads LINE and straight 2D/3D POLYLINE/LWPOLYLINE segments, merging
endpoints within 1 mm after conversion to meters. Closed polylines add a closing
segment. Optionally filter layers by comma-separated names. Curves, meshes, blocks,
duplicate or zero-length bars, and disconnected structures are rejected. Interior
crossings are not split into joints. This is a limited wireframe importer, not a
complete CAD interpreter.

Source stages are bins of bar mean elevation, starting from the lowest mean, using
the chosen height interval. All nodes within 1 mm of minimum Z are fixed in translation.
A single uniform section/material is initially assigned. One downward installation
load is placed at the highest endpoint of each nonzero source stage. These inferred
assumptions may be unsuitable for your structure: inspect the Input model tab and
download/edit/re-upload the Excel template to define actual supports, profiles,
stages and loads.

The interactive prototype limits uploaded files to 5 MB, 250 nodes and 500 bars.
The solver API itself is independent of these UI limits.

## Completed dome (rigid frame)

Choose this mode in the sidebar to retain the independent 49-node, 128-bar frame
demo. It includes rotations and rigid connections. Edit circular-tube diameter,
thickness and elastic modulus, then click **Run analysis**. Download a ZIP with
JSON, CSV, a report and a standalone HTML viewer. This completed-frame calculation
has no construction stages; it is distinct from the pin-jointed stage model.

## Validation and limitations

```bash
.venv/bin/python -m pytest -q tests
cd prototypes/rigid-frame
../../.venv/bin/python -m unittest discover -s tests -v
```

Tests cover analytical tripod and axial-member solutions, mechanisms, self-weight
balance, inactive bars/nodes, Euler ratios, transient loads, Excel round trips,
DXF conversion/errors, plots, and real Streamlit form and slider interactions.

This is a demonstration prototype. It does not authorize real construction or
structural design. No nonlinear analysis, erection-history stress accumulation,
connection checks, temporary shoring, or code-based capacity checks are included.
The two models have different assumptions and should not be expected to agree.
