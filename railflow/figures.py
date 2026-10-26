"""Standard model figures (static PNG): trip-length fits, deterrence functions, LA validation, flow maps.

``flow_map`` is public so that projects can draw their own extents."""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, LogNorm, TwoSlopeNorm
import shapely
from . import config as C

SURF = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; GRID = "#e4e3df"
BLUE = "#2a78d6"; ORANGE = "#eb6834"; AQUA = "#1baf7a"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
seq_cmap = LinearSegmentedColormap.from_list("seq", SEQ)
div_cmap = LinearSegmentedColormap.from_list("div", ["#256abf", "#86b6ef", "#f0efec", "#ec8a89", "#c53434"])

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False,
})


def tld_figures():
    obs = np.load(C.WORK / "tld_obs.npy"); mod = np.load(C.WORK / "tld_modelA.npy")
    bands = np.array(json.load(open(C.WORK / "la_index.json"))["bands"])
    mids = np.sqrt(np.maximum(bands[:-1], 1.0) * bands[1:])
    for k, lab in [(0, "internal"), (1, "external")]:
        fig, axs = plt.subplots(3, 4, figsize=(13, 8.2), sharex=True)
        for r, ax in enumerate(axs.flat):
            if r >= len(C.REGIONS):
                ax.axis("off"); continue
            o = obs[r, k] / obs[r, k].sum(); m = mod[r, k] / mod[r, k].sum()
            ax.bar(mids, o, width=np.diff(bands) * 0.85, color=BLUE, alpha=0.55, label="Observed (ORR Table 1595)")
            ax.plot(mids, m, color=ORANGE, lw=2, marker="o", ms=3, label="Model A")
            ax.set_xscale("log"); ax.set_xlim(1.5, 1200)
            mo = (obs[r, k] * mids).sum() / obs[r, k].sum(); mm = (mod[r, k] * mids).sum() / mod[r, k].sum()
            ax.set_title(f"{C.REGIONS[r]}\nmean {mo:.0f} km obs / {mm:.0f} km model", fontsize=9)
            ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
        axs[0, 0].legend(loc="upper right", fontsize=8)
        for ax in axs[-1]:
            ax.set_xlabel("Distance between local authorities (km, network)")
        fig.suptitle(f"Trip length distributions - {lab} journeys by government region (2024-25)", fontweight="bold", x=0.01, ha="left")
        fig.tight_layout()
        fig.savefig(C.FIG / f"tld_fit_{lab}.png", dpi=150); plt.close(fig)


def deterrence_figure():
    p = pd.read_csv(C.TAB / "deterrence_parameters.csv")
    d = np.linspace(1, 800, 2000)
    fig, axs = plt.subplots(3, 4, figsize=(13, 8), sharex=True)
    for r, ax in enumerate(axs.flat):
        if r >= len(p):
            ax.axis("off"); continue
        q = p.iloc[r]
        fi = np.exp(-(np.log(d) - q.mu_int) ** 2 / (2 * q.sigma_int ** 2)) / (d * q.sigma_int)
        fe = np.exp(q.gamma_ext) * np.exp(-(np.log(d) - q.mu_ext) ** 2 / (2 * q.sigma_ext ** 2)) / (d * q.sigma_ext)
        s = max(fi.max(), fe.max())
        ax.plot(d, fi / s, color=BLUE, lw=2, label="Internal")
        ax.plot(d, fe / s, color=ORANGE, lw=2, label="External")
        ax.set_xscale("log"); ax.set_title(q.region)
    axs[0, 0].legend(fontsize=8)
    for ax in axs[-1]:
        ax.set_xlabel("Network distance (km)")
    fig.suptitle("Calibrated deterrence functions f(c) (log-normal), scaled to 1 at the peak", fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(C.FIG / "deterrence_functions.png", dpi=150); plt.close(fig)


def la_validation():
    v = pd.read_csv(C.TAB / "la_pair_validation.csv")
    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    x = v.observed / 1e3; y = v.modelA / 1e3
    ok = (x > 0) & (y > 0)
    ax.scatter(x[ok], y[ok], s=9, color=BLUE, alpha=0.35, edgecolor="none")
    lim = [0.01, max(x.max(), y.max()) * 1.5]
    ax.plot(lim, lim, color=INK2, lw=1, ls="--")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Observed journeys, ORR Table 1595 (thousands per year)")
    ax.set_ylabel("Model A journeys (thousands per year)")
    s = json.load(open(C.TAB / "validation_summary.json"))
    ax.set_title("Local-authority pair flows: Model A vs observed", loc="left")
    ax.text(0.03, 0.97, f"{s['la_pairs']:,} LA pairs\nR² (log) = {s['r2_log_A']:.2f}\nR² (linear) = {s['r2_lin_A']:.2f}",
            transform=ax.transAxes, va="top", color=INK2)
    fig.tight_layout(); fig.savefig(C.FIG / "la_pair_validation.png", dpi=150); plt.close(fig)


def flow_map(edges, col, bbox, fname, title, maxw=7.0, vmin_share=0.002, labels=None, st=None):
    e = edges
    if bbox:
        x0, y0, x1, y1 = bbox
        e = e.cx[x0:x1, y0:y1]
    f = e[col].to_numpy()
    fmax = np.quantile(f[f > 0], 0.999)
    keep = f > fmax * vmin_share
    e = e[keep]; f = f[keep]
    order = np.argsort(f)
    segs = [np.asarray(g.coords) for g in e.geometry.values[order]]
    w = 0.25 + maxw * np.clip(f[order] / fmax, 0, 1)
    norm = LogNorm(vmin=fmax * vmin_share, vmax=fmax)
    if bbox:
        asp = (bbox[3] - bbox[1]) / (bbox[2] - bbox[0])
        fig, ax = plt.subplots(figsize=(12, 12 * asp + 0.9))
    else:
        fig, ax = plt.subplots(figsize=(8.5, 13))
    base = edges.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]] if bbox else edges
    ax.add_collection(LineCollection([np.asarray(g.coords) for g in base.geometry.values], colors="#dcdbd6", linewidths=0.4))
    lc = LineCollection(segs, linewidths=w, colors=seq_cmap(norm(f[order])), capstyle="round")
    ax.add_collection(lc)
    if labels is not None and st is not None:
        s = st[st.crs.isin(labels)]
        ax.scatter(s.x, s.y, s=10, color=INK, zorder=5)
        for _, r in s.iterrows():
            ax.annotate(r["name"].replace("London ", ""), (r.x, r.y), xytext=(4, 3), textcoords="offset points", fontsize=7.5, color=INK, zorder=6)
    if bbox:
        ax.set_xlim(bbox[0], bbox[2]); ax.set_ylim(bbox[1], bbox[3])
    else:
        ax.autoscale()
    ax.set_aspect("equal"); ax.set_axis_off()
    sm_ = plt.cm.ScalarMappable(norm=norm, cmap=seq_cmap)
    cb = fig.colorbar(sm_, ax=ax, shrink=0.45, pad=0.01)
    cb.set_label("Passengers per average weekday (both directions)", color=INK2)
    ax.set_title(title, loc="left")
    fig.tight_layout(); fig.savefig(C.FIG / fname, dpi=160); plt.close(fig)


def flow_maps(col="flow_TB_awd"):
    edges = gpd.read_parquet(C.WORK / "edge_flows.parquet")
    edges = edges[edges.kind != "tube"]
    st = pd.read_csv(C.WORK / "stations.csv")
    flow_map(edges, col, None, "flows_gb.png",
             f"Modelled rail passenger flows, average weekday {C.BASE_YEAR} (Model B)", maxw=5,
             labels=["MAN", "BHM", "LDS", "GLC", "EDB", "BRI", "CDF", "NCL", "WAT", "SOU"], st=st)
    flow_map(edges, col, C.LONDON_BBOX, "flows_london.png",
             "London: modelled passenger flows, average weekday (Model B)", maxw=10, vmin_share=0.004,
             labels=["WAT", "VIC", "LBG", "LST", "PAD", "EUS", "KGX", "SRA", "CLJ", "ECR", "WIM"], st=st)


def main(which=("tld", "det", "la", "flows")):
    if "tld" in which: tld_figures()
    if "det" in which: deterrence_figure()
    if "la" in which: la_validation()
    if "flows" in which: flow_maps()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or ("tld", "det", "la", "flows"))
