Stage-by-Stage Construction Analysis for Steel Domes

A hackathon prototype that shows how forces and stability in a steel dome change as its bars are installed.

Disclaimer: this is a demonstration prototype. It must not be used to authorize a real assembly.

1. Problem

At a company that designs and manufactures steel domes, the structure must be stable during construction, not only once it is finished. The idea is to analyze the structure every time one or several bars are installed, with the user defining how many.

2. Hackathon goal

Using a small example dome, show how these quantities evolve at each installation stage:

Axial force and stress in the bars.
Node displacements.
Support reactions.
Stability (detecting whether the active structure is a mechanism).

The focus is on making the calculation work and being able to explain it, not on delivering a complete product.

3. Calculation model
3D pin-jointed truss: bars carry axial force only. Each node has 3 degrees of freedom (x, y, z).
Loads:
Accumulated self-weight of the bars already installed.
Installation load (for example, the weight of a person) at the node or bar assigned to each stage.
Stages: start with the first ring already installed and activate bars per stage (1, 3 or N, as defined by the user).
Solution: at each stage, a new equilibrium is solved using only the active bars. Bars not yet installed contribute neither weight nor stiffness.
Stability: if the stiffness matrix is singular or nearly singular, the stage is flagged as "unstable" instead of crashing.
Buckling indicator (optional): ratio between compressive force and Euler load, Pcr = π²EI/L².
4. Inputs (fixed Excel template)
Sheet	Columns
Nodes	ID, x, y, z
Bars	ID, node i, node j, profile, installation stage
Profiles	name, area, moment of inertia (optional), elastic modulus E, density or weight per meter
Supports	node, restraints (x, y, z)
Loads	stage, application node, installation load magnitude
Criteria	allowable stress or yield strength

Also, a validation case: a simple truss with a hand-calculated solution or, if available, a dome analyzed in SAP2000 or RISA.

5. Outputs
3D view of the dome colored by stress or utilization.
Slider to step through the stages.
Plot of maximum force versus stage.
Results table per bar and per stage, with Excel export.
Clear indication of unstable stages.
6. Proposed technology
Python with NumPy and SciPy (scipy.sparse).
Pandas and openpyxl to read and write Excel.
Plotly for the 3D view.
Streamlit as the interface.
7. Feasibility
Memory: not an issue. The stiffness matrix is sparse and takes only a few MB, even for large domes.
Time: each stage solves in milliseconds, so running through all stages takes seconds or a few minutes.
The real difficulty is the physics: mechanisms during assembly, and the difference between a truss and real connections.
8. Plan (4–5 hours)
Hour	Task
0:00–0:30	Excel template and a script that generates an example dome (about 60 bars)
0:30–1:30	3D truss solver, supports, axial forces and reactions. Validate with a hand-calculated case
1:30–2:15	Stage loop, accumulated self-weight, installation load and instability detection
2:15–3:30	Streamlit interface with Excel upload, slider and 3D view
3:30–4:15	Per-stage plot, table and export
4:15–5:00	Polish, demo and list of limitations
9. Out of scope
CAD import.
Free-form model editing.
Multiple design codes and load combinations.
Moments, local bending, code-based buckling checks and connection capacity.
Real friction, shoring, cranes or temporary cables.
Detailed physical assembly history and nonlinear (P-Δ) analysis.
Polished interface.
10. Limitations
The pin-jointed truss is conservative: it may declare unstable something that actually stands thanks to rigid connections.
Solving each stage from scratch is an approximation of the real process.
Results are not a safety approval.
11. After the hackathon
Beam (frame) elements with 6 degrees of freedom per node.
Buckling and code checks (AISC or other).
CAD or DXF import.
P-Δ analysis and temporary shoring.
Assembly sequence optimization.
