"""Generate a synthetic dome Excel template from the repository root.

Usage: python examples/generate_dome.py --rings 4 --out data/example_dome.xlsx
"""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from domestage.demo_model import generate_demo_dome
from domestage.io_excel import write_template


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rings', type=int, default=4)
    parser.add_argument('--sides', type=int, default=12)
    parser.add_argument('--radius', type=float, default=6.)
    parser.add_argument('--height', type=float, default=3.5)
    parser.add_argument('--out', type=Path, default=Path('data/example_dome.xlsx'))
    args = parser.parse_args()
    model = generate_demo_dome(args.rings, args.sides, args.radius, args.height)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_template(model, args.out)
    print(f'Wrote {len(model.nodes)} nodes and {len(model.bars)} bars to {args.out}')
