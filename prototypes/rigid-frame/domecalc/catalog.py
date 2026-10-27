"""Valores elásticos nominales y catálogo geométrico editable, en SI."""
from .core import Material, Section

MATERIALS = {
    'Acero': Material(E=200e9, nu=.30, density=7850.),
    'Aluminio': Material(E=69e9, nu=.33, density=2700.),
}
# Diámetro exterior y espesor reales nominales; no diámetro nominal de tubería.
HSS = {
    'HSS circular 2″ × 1/8″': (.0508, .003175),
    'HSS circular 3″ × 1/8″': (.0762, .003175),
    'HSS circular 4″ × 1/8″': (.1016, .003175),
    'HSS circular 4″ × 3/16″': (.1016, .0047625),
    'HSS circular 5″ × 3/16″': (.127, .0047625),
    'HSS circular 6″ × 1/4″': (.1524, .00635),
    'HSS circular 8″ × 1/4″': (.2032, .00635),
}


def properties(material_name, profile_name):
    material = MATERIALS[material_name]
    diameter, thickness = HSS[profile_name]
    section = Section.circular(diameter, thickness)
    return material, section
