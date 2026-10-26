"""Assign station-to-station matrices to the rail network.

All-or-nothing assignment on the network-cost shortest path (the same costs as
the distance skim). For every origin station a shortest-path tree is built
(Dijkstra) and the demand to every destination is pushed back up the tree, so
each edge receives the sum of all OD flows routed over it.

Matrices assigned: Model A (AWD), Model B (AWD) and Model B (annual, for the
passenger-km check). Edge flows are two-way totals (the all-day matrix is
symmetric).

``assign_matrices`` is reusable: projects can assign their own matrices (a
subset of flows, a scenario) on the same network (see railflow.api).

Outputs of ``main``:
  outputs/model/edge_flows.parquet     edges + flow columns, BNG geometry
  outputs/gis/rail_flows.gpkg          layer 'edges' for GIS use
  outputs/model/station_throughput.csv passengers passing through / using each station
"""
import time
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from numba import njit
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from . import config as C


def collapsed(edges, n):
    a = np.minimum(edges.u, edges.v).to_numpy(); b = np.maximum(edges.u, edges.v).to_numpy()
    df = pd.DataFrame({"a": a, "b": b, "w": edges.cost_m.to_numpy(), "eid": np.arange(len(edges))})
    df = df.sort_values("w").drop_duplicates(["a", "b"])
    r = np.r_[df.a, df.b]; c = np.r_[df.b, df.a]; w = np.r_[df.w, df.w]; e = np.r_[df.eid, df.eid]
    G = csr_matrix((w, (r, c)), shape=(n, n))
    E = csr_matrix((e + 1, (r, c)), shape=(n, n))   # +1 so edge 0 is not dropped as an explicit zero
    E.sort_indices(); G.sort_indices()
    return G, E


@njit(cache=True)
def push_up(order, pred, node_flow, indptr, indices, eids, edge_flow):
    # node_flow: (k, N) demand ending at each node; edge_flow: (k, n_edges)
    k = node_flow.shape[0]
    for v in order:
        p = pred[v]
        if p < 0:
            continue
        # find edge id for (p, v)
        e = -1
        for q in range(indptr[v], indptr[v + 1]):
            if indices[q] == p:
                e = eids[q] - 1
                break
        for m in range(k):
            f = node_flow[m, v]
            if f != 0.0:
                node_flow[m, p] += f
                edge_flow[m, e] += f


def assign_matrices(mats, edges, nodes, snode, verbose=True):
    """All-or-nothing assignment of one or more S x S matrices (same station order).

    Returns an array (len(mats), n_edges) of two-way edge flows.
    """
    t0 = time.time()
    T = [np.asarray(m, dtype=np.float64) for m in mats]
    N = len(nodes)
    G, E = collapsed(edges, N)
    edge_flow = np.zeros((len(T), len(edges)))
    S = len(snode)
    rows = np.flatnonzero(sum(t.sum(1) for t in T) > 0)
    for k, s in enumerate(rows):
        row = np.stack([t[s] for t in T])
        dist, pred = dijkstra(G, directed=False, indices=snode[s], return_predecessors=True)
        node_flow = np.zeros((len(T), N))
        for m in range(len(T)):
            np.add.at(node_flow[m], snode, row[m])
        reach = np.flatnonzero(np.isfinite(dist))
        order = reach[np.argsort(-dist[reach], kind="stable")]
        push_up(order, pred.astype(np.int64), node_flow, E.indptr, E.indices, E.data.astype(np.int64), edge_flow)
        if verbose and k % 500 == 0:
            print(f"  origin {k}/{len(rows)} ({time.time()-t0:.0f}s)", flush=True)
    return edge_flow


def main():
    t0 = time.time()
    edges = gpd.read_parquet(C.WORK / "net_edges.parquet")
    nodes = np.load(C.WORK / "net_nodes.npy")
    sn = pd.read_csv(C.WORK / "station_nodes.csv")
    st = pd.read_csv(C.WORK / "stations.csv")
    mats = np.load(C.WORK / "matrices.npz")
    names = ["TA_awd", "TB_awd", "TA_ann", "TB_ann"]
    edge_flow = assign_matrices([mats[k] for k in names], edges, nodes, sn.node.to_numpy())
    for m, k in enumerate(names):
        edges[f"flow_{k}"] = edge_flow[m]
    edges.to_parquet(C.WORK / "edge_flows.parquet")
    (C.OUT / "gis").mkdir(exist_ok=True)
    keep = edges[(edges[["flow_TA_awd", "flow_TB_awd"]].max(axis=1) > 0) & (edges.kind != "tube")]
    keep.drop(columns=["way"]).to_crs(4326).to_file(C.OUT / "gis" / "rail_flows.gpkg", layer="edges", driver="GPKG")

    rail = edges.kind != "tube"
    pkm = (edges.flow_TB_ann * edges.length_m)[rail].sum() / 1e12
    print(f"assignment done ({time.time()-t0:.0f}s). Model B annual passenger-km on network: {pkm:.1f} bn "
          f"(ORR 2024-25: {C.ORR_PKM_BN} bn for {C.ORR_JOURNEYS_M:,.0f}m journeys; Table 1410 base = 1,532m journeys)")

    # station throughput: count edge crossings of a 150 m ring around each station
    ring = shapely.boundary(shapely.buffer(shapely.points(st.x, st.y), 150))
    edges = edges[edges.kind != "tube"].reset_index(drop=True)   # transfer links are not track
    tree = shapely.STRtree(edges.geometry.values)
    pairs = tree.query(ring, predicate="intersects")
    cross = shapely.get_num_geometries(shapely.intersection(ring[pairs[0]], edges.geometry.values[pairs[1]]))
    out = pd.DataFrame({"crs": st.crs})
    for k in ["TA_awd", "TB_awd"]:
        screen = np.bincount(pairs[0], weights=cross * edges[f"flow_{k}"].to_numpy()[pairs[1]], minlength=len(st))
        od = st.ee_awd.to_numpy()  # boardings + alightings
        out[f"through_{k}"] = np.maximum((screen - od) / 2, 0)
        out[f"total_{k}"] = out[f"through_{k}"] + od
    out["tracks_crossing_ring"] = np.bincount(pairs[0], weights=cross, minlength=len(st)) / 2
    out.to_csv(C.WORK / "station_throughput.csv", index=False)
    print(out.merge(st[["crs", "name"]]).sort_values("total_TB_awd", ascending=False).head(15).round(0).to_string())


if __name__ == "__main__":
    main()
