"""Example: demand weighting for the Split Ticket Calculator (STC).

The STC finds split-ticketing opportunities (STOs) for each flow and its saving
per journey, but not how many people travel on the flow or through each split
station. railflow adds that:

1. Journeys through each candidate split station: every OD pair whose modelled
   route passes the station (from the network-cost skim), with weekday and
   annual journeys. A station that is both a common split point and carries many
   through-journeys (the STC notes Pewsey) is where split ticketing can cost most.
2. Demand on the STC's own worked examples, with the stations along the route.
3. A join for STC outputs: annual journeys x saving gives an upper bound on the
   annual revenue at risk per flow (every traveller splits), which ranks STOs.

Run:  python examples/split_ticketing/split_ticket_demand.py
Optional: --stc summary_results.csv (STC primary output with origin, destination and saving columns)
"""
import argparse
import sys
import numpy as np
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import model, outdir, plt, BLUE, ORANGE, INK2  # noqa: E402

CANDIDATES = ["PEW", "WSB", "CLC", "MDN", "MKM", "HGD", "BDW", "NBY", "DID", "SWI", "CPM", "TRO", "FRO", "TAU", "CKN", "YVP"]
STC_EXAMPLES = [("WEY", "MKM", 121.70, "MDN", "Weymouth to Melksham, best split via Maiden Newton"),
                ("AMT", "BTO", 2.80, "CRN", "Aldermaston to Betchworth, best split via Crowthorne")]


def through_station_table(rf):
    rows = []
    T_ann = rf.matrix("B", "ann")
    for c in CANDIDATES:
        if c not in rf.index:
            continue
        p = rf.passing_through(c, "B", "awd")
        i = rf.idx(p.origin_crs.tolist()); j = rf.idx(p.destination_crs.tolist())
        ann = T_ann[i, j].sum() if len(p) else 0.0
        st = rf.stations.set_index("crs").loc[c]
        top = p.head(3)
        rows.append({"crs": c, "station": st["name"], "od_pairs_through": len(p), "weekday_journeys_through": p.trips.sum(),
                     "annual_journeys_through": ann, "station_entries_exits_annual": st.ee_all,
                     "largest_flows_through": "; ".join(f"{a}-{b} ({t:,.0f}/day)" for a, b, t in zip(top.origin, top.destination, top.trips))})
    return pd.DataFrame(rows).sort_values("annual_journeys_through", ascending=False)


def examples_table(rf):
    T = rf.matrix("B", "ann"); TA = rf.matrix("A", "ann")
    rows = []
    for o, d, saving, split, label in STC_EXAMPLES:
        i, j = rf.idx(o), rf.idx(d)
        journeys = T[i, j] + T[j, i]
        route = rf.route_stations(o, d)
        rows.append({"flow": label, "annual_journeys_modelB": journeys, "annual_journeys_modelA": TA[i, j] + TA[j, i],
                     "saving_per_journey_gbp": saving, "upper_bound_revenue_at_risk_gbp": journeys * saving,
                     "split_station_on_modelled_route": split in set(route.crs),
                     "modelled_route_km": rf.skim[i, j], "stations_on_route": " > ".join(route.name)})
    return pd.DataFrame(rows)


def join_stc(rf, path):
    s = pd.read_csv(path)
    cols = {c.lower(): c for c in s.columns}
    o = cols.get("origin"); d = cols.get("destination"); sav = next((cols[c] for c in cols if "saving" in c), None)
    if not (o and d and sav):
        raise SystemExit("STC file needs origin, destination and a savings column")
    name2crs = {n.upper(): c for n, c in zip(rf.stations.name, rf.stations.crs)}
    T = rf.matrix("B", "ann")
    def jn(a, b):
        a = rf.index.get(a, rf.index.get(name2crs.get(str(a).upper(), ""), None))
        b = rf.index.get(b, rf.index.get(name2crs.get(str(b).upper(), ""), None))
        return np.nan if a is None or b is None else T[a, b] + T[b, a]
    s["annual_journeys"] = [jn(a, b) for a, b in zip(s[o], s[d])]
    s["revenue_at_risk_upper_bound"] = s.annual_journeys * s[sav]
    return s.sort_values("revenue_at_risk_upper_bound", ascending=False)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--stc")
    a = ap.parse_args()
    rf = model(a.out); od = outdir(__file__)
    t = through_station_table(rf); t.round(1).to_csv(od / "split_station_through_journeys.csv", index=False)
    e = examples_table(rf); e.round(2).to_csv(od / "stc_examples_demand.csv", index=False)
    print(t.drop(columns="largest_flows_through").round(0).to_string()); print(e.round(1).T.to_string())
    if a.stc:
        join_stc(rf, a.stc).to_csv(od / "stc_ranked_by_revenue_at_risk.csv", index=False)
    # figure: annual journeys through each candidate split station vs its own entries/exits
    t = t.sort_values("annual_journeys_through")
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    y = np.arange(len(t))
    ax.barh(y + 0.2, t.annual_journeys_through / 1e6, height=0.38, color=BLUE, label="Journeys passing through (route via station)")
    ax.barh(y - 0.2, t.station_entries_exits_annual / 1e6, height=0.38, color=ORANGE, label="Entries + exits at the station")
    ax.set_yticks(y, t.station); ax.set_xlabel("Million journeys a year (railflow Model B, 2024-25)")
    ax.set_title("Candidate split stations: journeys passing through vs using the station", loc="left")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout(); fig.savefig(od / "split_station_through_journeys.png", dpi=150)
    print(f"outputs in {od}")


if __name__ == "__main__":
    main()
