"""Example: model-based flow features for the Flow Classification (Integrated Fares Model) work.

The preliminary k-means model classified 15,072 PMS flows for London Overground
and Greater Anglia using ticket types, distance and station usage. Two of its
stated limitations are missing or inconsistent route mileages and no measure of
how many people travel on each flow. railflow provides both, for every station pair:

  network_km      route distance on the rail network (fills missing mileages)
  crowfly_km      straight-line distance
  annual_journeys modelled journeys on the flow (Model B, both directions)
  commute_share   share of the flow's journeys made on season tickets (endpoint
                  season shares weighted by modelled journeys)
  weekday_ratio   modelled weekday journeys x 320 / annual journeys (commuter flows > 1)
  max_station_ee  larger of the two stations' annual entries + exits (log in the model)

This script builds those features for every flow touching a Greater Anglia or
London Overground station, runs a five-cluster k-means as in the preliminary
model, and reports each cluster's share of flows *and of journeys* (the
quantity that matters for revenue and customer impact).

Run:  python examples/flow_classification/flow_features.py
Join these features to the PMS flow list on origin and destination CRS/NLC.
"""
import argparse
import sys
import numpy as np
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import model, outdir, plt, BLUE, MUTED, INK2  # noqa: E402

OPERATORS = ["Greater Anglia", "London Overground"]
MIN_ANNUAL = 100          # ignore flows with fewer modelled journeys a year


def features(rf):
    st = rf.stations
    T = rf.matrix("B", "ann"); W = rf.matrix("B", "awd")
    U = T + T.T; UW = W + W.T
    tocs = st.sfo.fillna("").str.contains("|".join(OPERATORS)).to_numpy()
    iu = np.triu_indices(len(st), 1)
    keep = (tocs[iu[0]] | tocs[iu[1]]) & (U[iu] >= MIN_ANNUAL)
    i, j = iu[0][keep], iu[1][keep]
    xy = st[["x", "y"]].to_numpy()
    ss = st.season_share.fillna(0).to_numpy(); ee = st.ee_all.to_numpy()
    f = pd.DataFrame({
        "origin_crs": st.crs.to_numpy()[i], "destination_crs": st.crs.to_numpy()[j],
        "origin": st.name.to_numpy()[i], "destination": st.name.to_numpy()[j],
        "network_km": rf.skim[i, j], "crowfly_km": np.hypot(*(xy[i] - xy[j]).T) / 1000,
        "annual_journeys": U[i, j], "weekday_journeys": UW[i, j],
        "commute_share": (ss[i] * ee[i] + ss[j] * ee[j]) / (ee[i] + ee[j]),
        "max_station_ee": np.maximum(ee[i], ee[j]),
    })
    f["weekday_ratio"] = f.weekday_journeys * 320 / f.annual_journeys
    return f


def kmeans(X, k=5, seed=0, iters=100, restarts=10):
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(restarts):
        c = X[rng.choice(len(X), k, replace=False)]
        for _ in range(iters):
            lab = np.argmin(((X[:, None, :] - c[None]) ** 2).sum(-1), 1)
            new = np.array([X[lab == m].mean(0) if (lab == m).any() else c[m] for m in range(k)])
            if np.allclose(new, c):
                break
            c = new
        inertia = ((X - c[lab]) ** 2).sum()
        if best is None or inertia < best[0]:
            best = (inertia, lab, c)
    return best[1]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); a = ap.parse_args()
    rf = model(a.out); od = outdir(__file__)
    f = features(rf)
    Z = pd.DataFrame({"crowfly_km": f.crowfly_km, "network_km": f.network_km, "log_journeys": np.log(f.annual_journeys),
                      "commute_share": f.commute_share, "log_max_ee": np.log(f.max_station_ee)})
    X = ((Z - Z.mean()) / Z.std()).to_numpy(copy=True)
    X[:, 0] *= 2                       # distance weighted up, as in the preliminary model
    f["cluster"] = kmeans(X)
    summ = f.groupby("cluster").agg(flows=("origin", "size"), journeys=("annual_journeys", "sum"),
                                    crowfly_km_median=("crowfly_km", "median"), network_km_median=("network_km", "median"),
                                    journeys_per_flow_median=("annual_journeys", "median"), commute_share=("commute_share", "median"),
                                    weekday_ratio=("weekday_ratio", "median"), max_station_ee_median=("max_station_ee", "median"))
    summ["share_of_flows"] = summ.flows / summ.flows.sum(); summ["share_of_journeys"] = summ.journeys / summ.journeys.sum()
    summ = summ.sort_values("crowfly_km_median")
    order = {c: n for n, c in enumerate(summ.index)}
    f["cluster"] = f.cluster.map(order); summ.index = range(len(summ))
    f.round(3).to_csv(od / "flow_features_ga_lo.csv.gz", index=False, compression="gzip")
    summ.round(3).to_csv(od / "cluster_summary.csv")
    print(f"{len(f):,} flows; {f.annual_journeys.sum()/1e6:.1f}m journeys a year")
    print(summ.round(2).to_string())
    # small multiples: each cluster highlighted against all flows
    fig, axs = plt.subplots(2, 3, figsize=(10, 6.6), sharex=True, sharey=True)
    axs = axs.ravel(); axs[5].set_visible(False)
    for k, ax in enumerate(axs[:5]):
        ax.scatter(f.crowfly_km, f.annual_journeys, s=3, color=MUTED, edgecolor="none")
        g = f[f.cluster == k]
        ax.scatter(g.crowfly_km, g.annual_journeys, s=4, color=BLUE, edgecolor="none")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_title(f"Cluster {k}: {summ.share_of_flows[k]:.0%} of flows,\n{summ.share_of_journeys[k]:.0%} of journeys", fontsize=9)
        if k >= 2: ax.set_xlabel("Crow-fly km")
        if k % 3 == 0: ax.set_ylabel("Modelled journeys a year")
    axs[2].tick_params(labelbottom=True)
    fig.tight_layout(); fig.savefig(od / "clusters_distance_vs_journeys.png", dpi=150)
    print(f"outputs in {od}")


if __name__ == "__main__":
    main()
