"""Read-only access to a railflow model run, for use by other projects.

    from railflow.api import RailFlow
    rf = RailFlow("path/to/outputs")           # the folder written by `railflow run`
    rf.stations.head()                          # trip ends, region, LA, throughput
    T = rf.matrix("B", "awd")                  # S x S station-to-station trips (average weekday)
    rf.od("B", "awd", min_trips=1)             # long table of station pairs
    rf.screenline("VXH", "WAT")                # two-way corridor flow between two stations
    rf.passing_through("PEW")                  # OD pairs whose route passes a station
    rf.route_stations("WEY", "MKM")            # stations on the modelled route
    flows = rf.assign(T_subset)                # edge flows for any matrix on the same network

Station order everywhere follows ``rf.stations`` (CRS codes in ``rf.crs``).
"""
from functools import cached_property
from pathlib import Path
import json
import numpy as np
import pandas as pd


class RailFlow:
    def __init__(self, out_dir="outputs"):
        self.out = Path(out_dir)
        self.dir = self.out / "model"
        if not (self.dir / "matrices.npz").exists():
            raise FileNotFoundError(f"No model run found in {self.dir} (expected matrices.npz). Run `railflow run` first.")

    # ------------------------------------------------------------ tables
    @cached_property
    def stations(self) -> pd.DataFrame:
        st = pd.read_csv(self.dir / "stations.csv")
        for f, cols in [("station_la.csv", ["crs", "la"]), ("station_throughput.csv", None), ("station_nodes.csv", ["crs", "node", "snap_m"])]:
            p = self.dir / f
            if p.exists():
                t = pd.read_csv(p)
                st = st.merge(t[cols] if cols else t, on="crs", how="left")
        return st

    @cached_property
    def crs(self) -> np.ndarray:
        return self.stations.crs.to_numpy()

    @cached_property
    def index(self) -> dict:
        return {c: i for i, c in enumerate(self.crs)}

    def idx(self, crs):
        return self.index[crs] if isinstance(crs, str) else np.array([self.index[c] for c in crs])

    @cached_property
    def metadata(self) -> dict:
        p = self.dir / "metadata.json"
        return json.loads(p.read_text()) if p.exists() else {}

    # ---------------------------------------------------------- matrices
    @cached_property
    def _mats(self):
        return np.load(self.dir / "matrices.npz")

    def matrix(self, model="B", period="awd") -> np.ndarray:
        """Station-to-station trips. model 'A' (synthetic gravity) or 'B' (fused); period 'awd' or 'ann'."""
        return self._mats[f"T{model.upper()}_{period}"].astype(np.float64)

    def od(self, model="B", period="awd", min_trips=0.05) -> pd.DataFrame:
        T = self.matrix(model, period)
        i, j = np.nonzero(T >= min_trips)
        st = self.stations
        return pd.DataFrame({"origin_crs": st.crs.to_numpy()[i], "origin": st.name.to_numpy()[i],
                             "destination_crs": st.crs.to_numpy()[j], "destination": st.name.to_numpy()[j],
                             "trips": T[i, j], "network_km": self.skim[i, j]})

    @cached_property
    def skim(self) -> np.ndarray:
        """Network cost (km) between stations: shortest path incl. penalties and access legs."""
        return np.load(self.dir / "skim_cost_km.npy")

    # ----------------------------------------------------------- network
    @cached_property
    def edges(self):
        import geopandas as gpd
        p = self.dir / "edge_flows.parquet"
        return gpd.read_parquet(p if p.exists() else self.dir / "net_edges.parquet")

    @cached_property
    def nodes(self) -> np.ndarray:
        return np.load(self.dir / "net_nodes.npy")

    @cached_property
    def _graph(self):
        from .assignment import collapsed
        return collapsed(self.edges, len(self.nodes))

    def route_edges(self, o, d):
        """Edge ids on the shortest network path between two stations (by CRS)."""
        from scipy.sparse.csgraph import dijkstra
        G, E = self._graph
        st = self.stations.set_index("crs")
        a, b = int(st.loc[o, "node"]), int(st.loc[d, "node"])
        dist, pred = dijkstra(G, directed=False, indices=a, return_predecessors=True)
        if not np.isfinite(dist[b]):
            return []
        out, v = [], b
        while v != a:
            p = pred[v]
            lo, hi = E.indptr[v], E.indptr[v + 1]
            q = np.flatnonzero(E.indices[lo:hi] == p)
            out.append(int(E.data[lo + q[0]] - 1)); v = p
        return out[::-1]

    def route_stations(self, o, d, tol_km=0.3) -> pd.DataFrame:
        """Stations lying on the modelled route from o to d, in order (uses the network-cost skim)."""
        i, j = self.index[o], self.index[d]
        sk = self.skim
        on = sk[i] + sk[:, j] <= sk[i, j] + tol_km
        st = self.stations.loc[on, ["crs", "name"]].copy()
        st["km_from_origin"] = sk[i, on]
        return st.sort_values("km_from_origin").reset_index(drop=True)

    def passing_through(self, crs, model="B", period="awd", tol_km=0.3, min_trips=0.0) -> pd.DataFrame:
        """OD pairs (excluding the station itself) whose modelled route passes the station."""
        s = self.index[crs]
        sk = self.skim
        T = self.matrix(model, period)
        via = sk[:, [s]] + sk[[s], :] <= sk + tol_km
        via[s, :] = False; via[:, s] = False
        np.fill_diagonal(via, False)
        i, j = np.nonzero(via & (T > min_trips))
        st = self.stations
        return pd.DataFrame({"origin_crs": st.crs.to_numpy()[i], "destination_crs": st.crs.to_numpy()[j],
                             "origin": st.name.to_numpy()[i], "destination": st.name.to_numpy()[j],
                             "trips": T[i, j], "network_km": sk[i, j]}).sort_values("trips", ascending=False)

    # ------------------------------------------------------------- flows
    def screenline(self, a, b, half_width_m=None, col="flow_TB_awd") -> dict:
        """Two-way flow crossing a line drawn across all tracks midway between stations a and b."""
        import shapely
        e = self.edges
        e = e[e.kind != "tube"]
        st = self.stations.set_index("crs")
        pa, pb = st.loc[a, ["x", "y"]].to_numpy(float), st.loc[b, ["x", "y"]].to_numpy(float)
        m = (pa + pb) / 2; d = (pb - pa) / np.linalg.norm(pb - pa); n = np.array([-d[1], d[0]])
        half = half_width_m or max(400.0, 0.2 * np.linalg.norm(pb - pa))
        hit = e[e.intersects(shapely.LineString([m - n * half, m + n * half]))]
        return {"between": f"{a}-{b}", "flow": float(hit[col].sum()), "tracks_cut": int(len(hit))}

    def assign(self, *mats, verbose=False) -> np.ndarray:
        """Assign one or more S x S matrices; returns (len(mats), n_edges) edge flows aligned with rf.edges."""
        from .assignment import assign_matrices
        return assign_matrices(mats, self.edges, self.nodes, self.stations.node.to_numpy(), verbose=verbose)
