"""Permite ejecutar pytest desde la raíz sin instalar el prototipo."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
