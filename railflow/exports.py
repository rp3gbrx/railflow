"""User exports: station table, OD matrices as CSV, busiest lines."""
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from . import config as C


def main():
    st = pd.read_csv(C.WORK / "stations.csv")
    la = pd.read_csv(C.WORK / "station_la.csv")[["crs", "la"]]
    thr = pd.read_csv(C.WORK / "station_throughput.csv")
    sn = pd.read_csv(C.WORK / "station_nodes.csv")[["crs", "snap_m"]]
    m = np.load(C.WORK / "matrices.npz")
    out = st[["crs", "name", "region", "nlc", "sfo", "lat", "lon", "ee_all", "ee_season", "ee_awd", "O_awd", "D_awd", "annualisation_factor",
              "interchanges", "main_od_name", "main_od_journeys"]].merge(la, on="crs").merge(thr, on="crs").merge(sn, on="crs")
    out.round(1).to_csv(C.TAB / "station_trip_ends.csv", index=False)

    crs = st.crs.to_numpy(); name = st.name.to_numpy()
    for k in ["TA_awd", "TB_awd"]:
        T = m[k].astype(np.float64)
        i, j = np.nonzero(T >= 0.05)
        df = pd.DataFrame({"origin_crs": crs[i], "origin": name[i], "destination_crs": crs[j], "destination": name[j],
                           "trips_awd": T[i, j].round(2)})
        tag = "modelA" if k == "TA_awd" else "modelB"
        df.to_csv(C.OUT / f"od_matrix_awd_{tag}.csv.gz", index=False, compression="gzip")
        print(k, f"pairs >= 0.05/day: {len(df):,}; trips covered {df.trips_awd.sum()/T.sum():.4f}")

    # busiest named lines (highest section flow on each OSM-named line)
    e = gpd.read_parquet(C.WORK / "edge_flows.parquet")
    e = e[e.kind == "osm"]
    top = e.groupby("name").agg(km=("length_m", lambda s: s.sum() / 1000), max_flow_B=("flow_TB_awd", "max"),
                                max_flow_A=("flow_TA_awd", "max")).sort_values("max_flow_B", ascending=False)
    top.round(0).to_csv(C.TAB / "lines_max_flow.csv")
    print(top.head(10).round(0).to_string())


if __name__ == "__main__":
    main()
