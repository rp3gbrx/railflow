"""Example: passenger weights for the T3 & Cancellation prediction work.

T3 and cancellations are counted per train. Passengers experience them in
proportion to how many people are on the affected trains, which varies by an
order of magnitude between routes. railflow gives the weights needed to:

  * aggregate route-period T3 / cancellation rates to a passenger-weighted
    national figure (the PfPI idea applied to the prediction targets);
  * add passenger exposure as a feature or as sample weights in the XGBoost
    models, so errors on busy routes count for more;
  * convert predicted delay into passenger-minutes for prioritisation.

Outputs: passenger-km and journeys by region (each track section is assigned
to the region of its nearest station) and by named line, with each area's
share of track-km for comparison.

Run:  python examples/performance_weighting/passenger_weights.py

Weighting a route-period table (columns: area, period, t3) with these weights:
    w = pd.read_csv("outputs/weights_by_region.csv").set_index("region").pkm_share
    df["w"] = df.area.map(w);  national = (df.t3 * df.w).groupby(df.period).sum() / df.w.groupby(df.period).sum()
"""
import argparse
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import model, outdir, plt, BLUE, ORANGE  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); a = ap.parse_args()
    rf = model(a.out); od = outdir(__file__)
    e = rf.edges
    e = e[e.kind == "osm"].copy()
    st = rf.stations
    mid = np.column_stack([e.geometry.interpolate(0.5, normalized=True).x, e.geometry.interpolate(0.5, normalized=True).y])
    _, k = cKDTree(st[["x", "y"]].to_numpy()).query(mid)
    e["region"] = st.region.to_numpy()[k]
    e["pkm_awd"] = e.flow_TB_awd * e.length_m / 1000
    e["pkm_ann"] = e.flow_TB_ann * e.length_m / 1000
    T = rf.matrix("B", "ann")
    jr = pd.Series(T.sum(1), index=st.region).groupby(level=0).sum()
    r = e.groupby("region").agg(track_km=("length_m", lambda s: s.sum() / 1000), pkm_awd=("pkm_awd", "sum"), pkm_ann=("pkm_ann", "sum"))
    r["journeys_originating_ann"] = jr
    r["pkm_share"] = r.pkm_ann / r.pkm_ann.sum(); r["track_km_share"] = r.track_km / r.track_km.sum()
    r["pax_per_track_km_awd"] = r.pkm_awd / r.track_km
    r = r.sort_values("pkm_share", ascending=False)
    r.round(4).to_csv(od / "weights_by_region.csv")
    lines = e.dropna(subset=["name"]).groupby("name").agg(track_km=("length_m", lambda s: s.sum() / 1000), pkm_ann=("pkm_ann", "sum"),
                                                         peak_section_flow_awd=("flow_TB_awd", "max"))
    lines["pkm_share"] = lines.pkm_ann / e.pkm_ann.sum()
    lines = lines.sort_values("pkm_ann", ascending=False)
    lines.head(40).round(4).to_csv(od / "weights_by_line_top40.csv")
    print(r.round(3).to_string()); print(lines.head(12).round(3).to_string())
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    rr = r.sort_values("pkm_share")
    y = np.arange(len(rr))
    ax.barh(y + 0.2, rr.pkm_share * 100, height=0.38, color=BLUE, label="Share of passenger-km")
    ax.barh(y - 0.2, rr.track_km_share * 100, height=0.38, color=ORANGE, label="Share of track-km")
    ax.set_yticks(y, rr.index); ax.set_xlabel("% of Great Britain total (railflow Model B, 2024-25)")
    ax.set_title("Passenger weight vs network size by region", loc="left"); ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout(); fig.savefig(od / "pkm_vs_track_by_region.png", dpi=150)
    print(f"outputs in {od}")


if __name__ == "__main__":
    main()
