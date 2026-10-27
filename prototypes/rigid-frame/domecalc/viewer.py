"""Exporta el visor autocontenido sin depender de Codex ni conexión a internet."""
from html import escape
import json
from pathlib import Path


def export_viewer(result, path):
    nodes = [{"p": n["xyz_m"], "s": bool(n["fixed_dofs"]),
              "r": [v / 1000 for v in n["reaction"]], "rFixed": all(a in n["fixed_dofs"] for a in (3,4,5))} for n in result["nodes"]]
    bars = []
    for e in result["elements"]:
        stations = e["stations"]
        mid = min(stations, key=lambda s: abs(s["x_m"] - e["length_m"] / 2))
        bars.append({"i": e["i"], "j": e["j"], "l": e["length_m"], "layer": e["layer"],
                     "n": [s["N_Vy_Vz_T_My_Mz"][0] / 1000
                           for s in (stations[0], mid, stations[-1])]})
    bounds = [[min(n["p"][i] for n in nodes), max(n["p"][i] for n in nodes)] for i in range(3)]
    center = [(lo + hi) / 2 for lo,hi in bounds]
    diameter = max(sum((hi-lo)**2 for lo,hi in bounds)**.5 * 1.1, .001)
    data = {"nodes": nodes, "bars": bars, "meta": {k: result.get("configuration", {}).get(k) for k in ("material", "profile", "connections")},
            "center": center, "diameter": diameter}
    template = Path(__file__).with_name("viewer-template.html").read_text(encoding="utf-8")
    # El visor vive en srcdoc: escapar JSON tanto para script como para atributo HTML.
    payload = json.dumps(data, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    payload = payload.replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template.replace("__DOME_DATA__", escape(payload, quote=True)), encoding="utf-8")
    return target
