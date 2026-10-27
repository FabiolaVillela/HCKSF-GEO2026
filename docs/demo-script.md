# Demo script (~5 minutes)

Setup: `streamlit run src/domestage/app.py`, browser full-screen, example dome loaded, bars per stage = 1.
Rehearse once with a timer.

| Time | Say / do |
|---|---|
| 0:00 | **Problem.** A dome must be stable while it is built, not just when finished. We analyze it after every installed bar (or group of bars). Point at the disclaimer: demonstration prototype, not for authorizing assembly. |
| 0:45 | **Model.** 3D pin-jointed truss, 3 DOF per node. Only installed bars have weight and stiffness; each stage adds the installer's load. Show the sidebar: upload the Excel template, choose bars per stage. |
| 1:30 | **Walk the stages.** Drag the slider from stage 0. Gray bars are not installed yet; colors show stress. Mention the max-force plot and the reactions table. |
| 2:30 | **Instability.** Move to the unstable stage: red banner, "mechanism". Explain: singular stiffness matrix is reported as a result, never a crash. Change bars per stage to 3 and show the stage count and the instability change. |
| 3:30 | **Validation.** Tripod: hand calculation −471.4 N and 4.714e-5 m, matched by the solver (`docs/validation.md`). |
| 4:15 | **Export.** Click the Excel download; show the Summary sheet. |
| 4:30 | **Limitations and next steps.** Pins are conservative; no P-Δ, shoring, connections or code checks. Next: beam elements (prototype exists), AISC buckling, DXF import, sequence optimization. |
| 5:00 | Questions. |

## Slides (6)

1. Title and disclaimer
2. Why stage-by-stage analysis matters
3. Model and pipeline (Excel, stages, solver, results)
4. Live demo (switch to the app)
5. Validation: tripod hand calc vs solver
6. Limitations and next steps

## Backup plan

If the live app fails, show screenshots of: a stable stage, the unstable stage, the history plot.
