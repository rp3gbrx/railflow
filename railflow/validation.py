"""Validation of the distribution models against independent ORR data.

1. LA-pair flows (Table 1595) - Model A only (Model B is fitted to them).
2. Station 'main origin/destination' flows (Table 1410) - an independent,
   station-level check for both models: the largest observed flow of each station.
3. Regional internal shares and mean trip lengths; comparison with the
   ETC 2018 paper's Table 1 (7 regional groups, AM period, MND 2018).
"""
import json
import numpy as np
import pandas as pd
from . import config as C
from .distribution import Data, main_od_cells, fuse


def r2(a, b):
    return 1 - ((a - b) ** 2).sum() / ((a - a.mean()) ** 2).sum()


def st_crs(D, idx):
    return D.st.crs.to_numpy()[idx]


def main():
    D = Data()
    st = D.st
    m = np.load(C.WORK / "matrices.npz")
    TA, TB = m["TA_ann"].astype(float), m["TB_ann"].astype(float)
    out = {}
    UA = D.undirected_la(TA); UB = D.undirected_la(TB); O = D.obs_la
    iu = np.triu_indices(D.L)
    v = pd.DataFrame({"la1": np.array(D.las)[iu[0]], "la2": np.array(D.las)[iu[1]], "observed": O[iu], "modelA": UA[iu], "modelB": UB[iu],
                      "distance_km": D.d_la[iu]})
    v = v[(v.observed > 0) | (v.modelA > 1)]
    v.to_csv(C.TAB / "la_pair_validation.csv", index=False)
    pos = v[(v.observed > 0) & (v.modelA > 0)]
    out["la_pairs"] = int((v.observed > 0).sum())
    out["r2_lin_A"] = float(r2(pos.observed, pos.modelA))
    out["r2_log_A"] = float(r2(np.log(pos.observed), np.log(pos.modelA)))
    out["r2_lin_B"] = float(r2(pos.observed, pos.modelB))
    big = pos[pos.observed >= 100_000]
    out["la_pairs_100k"] = int(len(big))
    out["median_abs_pct_err_A_100k"] = float((100 * (big.modelA / big.observed - 1).abs()).median())

    # main OD flows (Table 1410), both directions. Model A never sees these.
    # Model B fixes them, so it is tested on a hold-out: 20% of the pairs are
    # withheld, Model B is rebuilt from the other 80%, and the withheld flows are predicted.
    cells = main_od_cells(D)
    rng = np.random.default_rng(42)
    hold = rng.random(len(cells)) < 0.2
    TB80, _, _ = fuse(TA, D, cells[~hold].reset_index(drop=True))
    TBla, _, _ = fuse(TA, D, cells.iloc[:0])          # LA totals only, no fixed cells
    i, j, J = cells.i.to_numpy(), cells.j.to_numpy(), cells.J.to_numpy()
    res = pd.DataFrame({"crs_i": st_crs(D, i), "crs_j": st_crs(D, j), "observed": J, "holdout": hold,
                        "modelA": TA[i, j] + TA[j, i], "modelB_LAonly": TBla[i, j] + TBla[j, i],
                        "modelB_80pct": TB80[i, j] + TB80[j, i], "modelB": TB[i, j] + TB[j, i]})
    res.to_csv(C.TAB / "main_od_validation.csv", index=False)
    h = res[res.holdout]
    for k in ["modelA", "modelB_LAonly", "modelB_80pct"]:
        out[f"holdout_{k}_median_ratio"] = float((h[k] / h.observed).median())
        out[f"holdout_{k}_r2_log"] = float(r2(np.log(h.observed), np.log(np.maximum(h[k], 1))))
        out[f"holdout_{k}_within_25pct"] = float(((h[k] / h.observed - 1).abs() <= 0.25).mean())
    out["holdout_pairs"] = int(hold.sum())
    out["main_od_share_of_journeys"] = float(J.sum() / D.O_ann.sum())

    # national mean trip length (network cost km) and regional summaries
    d = D.d
    for k, T in [("A", TA), ("B", TB)]:
        out[f"mean_trip_km_{k}"] = float((T * d).sum() / T.sum())
    out["orr_mean_trip_km_all_operators"] = C.ORR_PKM_BN * 1e3 / C.ORR_JOURNEYS_M
    out["annual_journeys_m"] = float(TA.sum() / 1e6)

    # paper Table 1 comparison (7 groups)
    grp = st.paper_group.to_numpy()
    rows = []
    for g in sorted(set(grp)):
        a = grp == g
        for k, T in [("A", TA), ("B", TB)]:
            Ti = T[np.ix_(a, a)]; di = d[np.ix_(a, a)]
            Te = T[np.ix_(a, ~a)]; de = d[np.ix_(a, ~a)]
            rows.append((g, k, (Ti * di).sum() / Ti.sum(), (Te * de).sum() / Te.sum(), Ti.sum() / (Ti.sum() + Te.sum())))
    pg = pd.DataFrame(rows, columns=["group", "model", "mean_km_int", "mean_km_ext", "internal_share"])
    pg["paper_AM_2018_int_km"] = [C.PAPER_TABLE1_KM[(g, "int")] for g in pg.group]
    pg["paper_AM_2018_ext_km"] = [C.PAPER_TABLE1_KM[(g, "ext")] for g in pg.group]
    pg.to_csv(C.TAB / "paper_table1_comparison.csv", index=False)
    json.dump(out, open(C.TAB / "validation_summary.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
    print(pg.round(2).to_string())


if __name__ == "__main__":
    main()
