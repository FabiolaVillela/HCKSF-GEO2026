"""Ejemplo sintético reproducible; no necesita un DXF privado."""
import math
from domecalc import Model, analyze, export
from domecalc.viewer import export_viewer


def example_model():
    nodes = []
    bars = []
    count = 16
    for radius, height in [(10., 0.), (8., 4.), (4.5, 7.)]:
        nodes.extend([[radius * math.cos(2 * math.pi * i / count),
                       radius * math.sin(2 * math.pi * i / count), height]
                      for i in range(count)])
    for ring in range(3):
        for i in range(count):
            bars.append((ring * count + i, ring * count + (i + 1) % count, "anillo"))
            if ring < 2:
                bars.append((ring * count + i, (ring + 1) * count + i, "meridiano"))
                bars.append((ring * count + i, (ring + 1) * count + (i + 1) % count, "diagonal"))
    apex = len(nodes)
    nodes.append([0., 0., 8.])
    bars.extend([(2 * count + i, apex, "corona") for i in range(count)])
    return Model(nodes, bars).pin_base()


if __name__ == "__main__":
    result = analyze(example_model())
    export(result, "output/demo")
    path = export_viewer(result, "output/demo/visor.html")
    print(f"Abrir en un navegador: {path.resolve()}")
    print(result["summary"])
