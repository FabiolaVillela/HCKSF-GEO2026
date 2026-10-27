# Validation

Run: `python validation/validate.py` (from the repo root). It compares hand calculations,
an independent NumPy reference, and `domestage.solver.solve_truss` (skipped until implemented).

Model: tripod, apex at (0,0,1), base nodes on a unit circle at z=0 (pinned),
A = 1e-4 m², E = 2e11 Pa, bar length L = √2 m.

## Case A: 1000 N vertical load at the apex

Vertical equilibrium at the apex, three equal bars at cos θ = 1/√2 to the vertical:

3·|F|/√2 = 1000, so F = −1000·√2/3 = **−471.40 N** (compression).

Bar shortening δ = F·L/(E·A) = 471.40·1.4142/(2e7) = 3.333e-5 m. The apex moves
vertically by δ/cos θ = **4.714e-5 m** downward.

## Case B: same load plus self-weight (ρ = 7850 kg/m³)

Weight per bar = ρ·A·L·g = 10.89 N, half to each end node. Apex receives 3·5.45 = 16.34 N,
so P = 1016.34 N and F = −P·√2/3 = **−479.10 N**. (Supports absorb their share directly.)

## Case C: only two bars installed

Two bars leave the apex free to move perpendicular to their plane: the reduced stiffness matrix
is singular. Expected: `stable = False`, no exception.

## Results

| Case | Quantity | Hand | Reference | Team solver |
|---|---|---|---|---|
| A | bar force [N] | −471.405 | −471.405 | _pending_ |
| A | apex uz [m] | −4.714e-5 | −4.714e-5 | _pending_ |
| B | bar force [N] | −479.105 | −479.105 | _pending_ |
| C | stable | False | False | _pending_ |

Fill the last column after `solver.py` lands; document any difference and its cause.

## Not yet covered

- A multi-ring dome checked against SAP2000/RISA or the rigid-frame prototype in `prototypes/rigid-frame/`
  (note: a frame with rigid joints will legitimately differ from a pin-jointed truss).
- The stage sequence (loads and weights accumulating across stages): add once `stages.py` lands.
