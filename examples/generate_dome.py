"""Generate a small synthetic dome (about 60 bars) as a StructureModel / Excel template.

OWNER: Role 2 (data I/O + example dome). Depends on: schema.py, io_excel.write_template.

Usage (target): python examples/generate_dome.py --rings 3 --out data/example_dome.xlsx
"""


def generate_dome(rings: int = 3, sides: int = 8, radius: float = 5.0):
    """Return a schema.StructureModel of a ring-based dome.

    - Rings from base (z = 0, supported) to the top node.
    - Bars: ring bars, meridian bars and diagonals.
    - Stage 0 = base ring (already installed); then one ring per group of stages.
    - One profile "TUBE" (e.g. area 5e-4 m2, E 200e9 Pa, density 7850 kg/m3).
    - One installation load of 1 kN (-z) per stage at the newest node.
    """
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit("TODO")
