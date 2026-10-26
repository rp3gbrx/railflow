"""Shared helpers for the examples: locate the model run and apply the chart style."""
import os
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from railflow.api import RailFlow  # noqa: E402

SURF = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; GRID = "#e4e3df"
BLUE = "#2a78d6"; ORANGE = "#eb6834"; AQUA = "#1baf7a"; MUTED = "#c9c8c2"
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "font.size": 9,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def model(out=None):
    """The railflow run to use: --out argument, RAILFLOW_OUTPUT_DIR, or <repo>/outputs."""
    out = out or os.environ.get("RAILFLOW_OUTPUT_DIR") or REPO / "outputs"
    return RailFlow(out)


def outdir(example_file):
    d = Path(example_file).resolve().parent / "outputs"
    d.mkdir(exist_ok=True)
    return d
