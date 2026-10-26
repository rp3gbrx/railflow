"""Rail network graph from the HOT OSM railways export, and distance skims.

* Topology comes from shared OSM vertices: two ways connect only where they
  share a vertex, so bridges and tunnels crossing without a junction stay
  apart (a geometric 'intersection' approach would wrongly join them).
* The HOT export has gaps (missing switch ways, and some missing route
  sections such as parts of the Tyne Valley and Bath - Bradford-on-Avon lines),
  so the graph is healed in two passes:
    (a) dead-end vertices are joined to the nearest vertex of another way
        within HEAL_SNAP_M (missing short switch / crossover ways);
    (b) remaining disconnected pieces are bridged to their nearest other
        piece (Boruvka rounds) if the gap is <= HEAL_BRIDGE_M. Bridges are
        straight 'synthetic' edges with a cost penalty and are flagged.
* Ways are split at junctions, way ends, connectors and station snap points;
  each edge keeps its own polyline for mapping.
* Stations snap to the nearest vertex of a *named* way (running line) within
  400 m, otherwise to the nearest vertex; the snap distance is added to the
  skim as an access leg.
* Northern Ireland is dropped (not in ORR Table 1410, not connected to GB).

Outputs:
  outputs/model/net_nodes.npy, net_edges.parquet, station_nodes.csv,
  outputs/model/skim_cost_km.npy (n_stations x n_stations network cost in km)
"""
import time
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix, coo_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from . import config as C

HEAL_SNAP_M = 30.0
HEAL_BRIDGE_M = 40_000.0
BRIDGE_PENALTY = 1.3


def comps(n, u, v):
    A = coo_matrix((np.ones(len(u)), (u, v)), shape=(n, n)).tocsr()
    return connected_components(A, directed=False)[1]


def nearest_other(tree, pts, own_lab, lab, kmax=4096, dmax=np.inf):
    """For each point, nearest tree point whose label differs from own_lab[i]."""
    out_d = np.full(len(pts), np.inf); out_i = np.full(len(pts), -1)
    todo = np.arange(len(pts)); k = 16
    while len(todo) and k <= kmax:
        d, i = tree.query(pts[todo], k=k, distance_upper_bound=dmax)
        i = np.where(np.isinf(d), 0, i)
        diff = (lab[i] != own_lab[todo][:, None]) & np.isfinite(d)
        has = diff.any(1)
        j = diff.argmax(1)
        r = np.flatnonzero(has)
        out_d[todo[r]] = d[r, j[r]]; out_i[todo[r]] = i[r, j[r]]
        # stop for points whose k-th neighbour is already beyond dmax
        exhausted = ~np.isfinite(d[:, -1])
        todo = todo[~has & ~exhausted]
        k *= 4
    return out_d, out_i


def build_graph():
    t0 = time.time()
    gdf = gpd.read_file(C.OSM_LINES, columns=["name", "adm1_name"], engine="pyogrio")
    gdf = gdf[gdf["adm1_name"] != "Northern Ireland"].to_crs(C.CRS_EPSG)
    gdf = gdf.explode(index_parts=False).reset_index(drop=True)
    gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].reset_index(drop=True)
    named = gdf["name"].notna().to_numpy()
    xy, way = shapely.get_coordinates(gdf.geometry.values, return_index=True)
    key = np.round(xy * 100).astype(np.int64)
    uniq, node = np.unique(key[:, 0] * 10_000_000_000 + key[:, 1], return_inverse=True)
    N = len(uniq)
    node_xy = np.zeros((N, 2)); node_xy[node] = xy
    first = np.r_[True, way[1:] != way[:-1]]
    last = np.r_[way[1:] != way[:-1], True]
    print(f"ways {len(gdf):,} vertices {len(xy):,} unique {N:,} ({time.time()-t0:.1f}s)")

    # raw vertex graph
    ru = node[:-1][~first[1:]]; rv = node[1:][~first[1:]]
    keep = ru != rv; ru, rv = ru[keep], rv[keep]
    deg = np.bincount(np.r_[ru, rv], minlength=N)
    node_way = np.full(N, -1); node_way[node] = way

    # (a) dead-end snapping
    dead = np.flatnonzero(deg == 1)
    tree = cKDTree(node_xy)
    d, i = nearest_other(tree, node_xy[dead], node_way[dead], node_way, kmax=64, dmax=HEAL_SNAP_M)
    ok = np.isfinite(d)
    con_a = pd.DataFrame({"u": dead[ok], "v": i[ok], "length_m": d[ok], "kind": "snap"})
    con_a = con_a[con_a.u != con_a.v]
    a = np.minimum(con_a.u, con_a.v); b = np.maximum(con_a.u, con_a.v)
    con_a = con_a.assign(u=a, v=b).drop_duplicates(["u", "v"])
    print(f"(a) dead-end snaps <= {HEAL_SNAP_M:.0f} m: {len(con_a):,}")

    # (b) Boruvka bridging between components
    U = np.r_[ru, con_a.u]; V = np.r_[rv, con_a.v]
    lab = comps(N, U, V)
    deg2 = np.bincount(np.r_[U, V], minlength=N)
    bridges = []
    for rnd in range(12):
        sizes = np.bincount(lab)
        ncomp = (sizes > 0).sum()
        if ncomp <= 1:
            break
        # candidate sources: dead ends (deg<=1); for components without dead ends use all nodes
        src = np.flatnonzero(deg2 <= 1)
        has_dead = np.zeros(len(sizes), bool); has_dead[lab[src]] = True
        extra = np.flatnonzero(~has_dead[lab] & (sizes[lab] < 5000))
        src = np.r_[src, extra]
        d, i = nearest_other(tree, node_xy[src], lab[src], lab, kmax=16384, dmax=HEAL_BRIDGE_M)
        cand = pd.DataFrame({"c": lab[src], "u": src, "v": i, "d": d})
        cand = cand[np.isfinite(cand.d)].sort_values("d").drop_duplicates("c")
        if cand.empty:
            break
        # union (keep only edges that still join different components, shortest first)
        parent = np.arange(len(sizes))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        added = 0
        for r in cand.itertuples():
            a_, b_ = find(lab[r.u]), find(lab[r.v])
            if a_ != b_:
                parent[a_] = b_; bridges.append((r.u, r.v, r.d)); added += 1
        roots = np.array([find(x) for x in range(len(sizes))])
        lab = roots[lab]
        deg2[[b[0] for b in bridges[-added:]]] += 1
        deg2[[b[1] for b in bridges[-added:]]] += 1
        print(f"(b) round {rnd}: components {ncomp:,} -> {(np.bincount(lab)>0).sum():,} (+{added} bridges)")
        if added == 0:
            break
    con_b = pd.DataFrame(bridges, columns=["u", "v", "length_m"]).assign(kind="bridge")
    sizes = np.bincount(lab)
    print(f"bridges added {len(con_b)}, total bridged length {con_b.length_m.sum()/1e3:,.1f} km; "
          f"remaining components {(sizes>0).sum()} (largest {sizes.max():,} of {N:,} vertices)")
    connectors = pd.concat([con_a, con_b], ignore_index=True)

    # station snapping
    st = pd.read_csv(C.WORK / "stations.csv")
    named_nodes = np.unique(node[named[way]])
    tn = cKDTree(node_xy[named_nodes])
    sxy = st[["x", "y"]].to_numpy()
    d1, i1 = tn.query(sxy); d2, i2 = tree.query(sxy)
    use_named = d1 <= 400
    snap_node = np.where(use_named, named_nodes[i1], i2)
    snap_m = np.where(use_named, d1, d2)

    # key vertices: way ends, junctions (deg != 2), connector ends, station snaps
    degh = np.bincount(np.r_[ru, rv, connectors.u, connectors.v], minlength=N)
    is_key = degh != 2
    is_key[node[first]] = True; is_key[node[last]] = True
    is_key[connectors.u.to_numpy(int)] = True; is_key[connectors.v.to_numpy(int)] = True
    is_key[snap_node] = True

    # split ways into edges at key vertices
    step = np.zeros(len(xy))
    step[1:] = np.hypot(*(xy[1:] - xy[:-1]).T); step[first] = 0
    kv = is_key[node]
    starts = kv & ~last
    seg_id = np.cumsum(starts) - 1
    step_seg = np.r_[-1, seg_id[:-1]]; step_seg[first] = -1
    nseg = int(starts.sum())
    seg_len = np.bincount(step_seg[step_seg >= 0], weights=step[step_seg >= 0], minlength=nseg)
    start_idx = np.flatnonzero(starts); key_idx = np.flatnonzero(kv)
    end_idx = key_idx[np.searchsorted(key_idx, start_idx, side="right")]
    e = pd.DataFrame({"u": node[start_idx], "v": node[end_idx], "length_m": seg_len,
                      "way": way[start_idx], "i0": start_idx, "i1": end_idx})
    e = e[e.u != e.v].reset_index(drop=True)
    e["named"] = named[e.way.to_numpy()]
    e["name"] = gdf["name"].to_numpy()[e.way.to_numpy()]
    e["kind"] = "osm"
    lens = (e.i1 - e.i0 + 1).to_numpy()
    idx = np.concatenate([np.arange(a, b + 1) for a, b in zip(e.i0, e.i1)])
    e["geometry"] = shapely.linestrings(xy[idx], indices=np.repeat(np.arange(len(e)), lens))
    e = e.drop(columns=["i0", "i1"])
    cg = shapely.linestrings(np.stack([node_xy[connectors.u.to_numpy(int)], node_xy[connectors.v.to_numpy(int)]], 1))
    ce = pd.DataFrame({"u": connectors.u.to_numpy(int), "v": connectors.v.to_numpy(int),
                       "length_m": connectors.length_m.to_numpy(), "way": -1, "named": False,
                       "name": None, "kind": connectors.kind.to_numpy(), "geometry": cg})
    edges = pd.concat([e, ce], ignore_index=True)
    pen = np.where(edges.kind == "bridge", BRIDGE_PENALTY, np.where(edges.named, 1.0, C.UNNAMED_WAY_PENALTY))
    edges["cost_m"] = edges.length_m * pen

    used = np.unique(np.r_[edges.u, edges.v, snap_node])
    remap = -np.ones(N, np.int64); remap[used] = np.arange(len(used))
    edges["u"] = remap[edges.u]; edges["v"] = remap[edges.v]
    st_nodes = pd.DataFrame({"crs": st.crs, "node": remap[snap_node], "snap_m": snap_m.round(1),
                             "snapped_to_named": use_named})
    print(f"graph: nodes {len(used):,} edges {len(edges):,} (osm {(edges.kind=='osm').sum():,}); "
          f"track length {edges.loc[edges.kind=='osm','length_m'].sum()/1e3:,.0f} km ({time.time()-t0:.1f}s)")
    # raw dead ends (before healing) on named ways - candidates for closing missing line sections
    dn = dead[named[node_way[dead]]]
    raw_dead = pd.DataFrame({"node": remap[dn], "name": gdf["name"].to_numpy()[node_way[dn]]})
    raw_dead = raw_dead[raw_dead.node >= 0]
    return node_xy[used], edges, st_nodes, st, raw_dead


def graph_matrix(edges, n, weight="cost_m"):
    a = np.minimum(edges.u, edges.v); b = np.maximum(edges.u, edges.v)
    g = pd.DataFrame({"a": a, "b": b, "w": edges[weight]}).groupby(["a", "b"], as_index=False)["w"].min()
    return csr_matrix((np.r_[g.w, g.w], (np.r_[g.a, g.b], np.r_[g.b, g.a])), shape=(n, n))


GAP_MAX_M = 40_000.0
GAP_PENALTY = 1.1


def close_named_gaps(nodes_xy, edges, raw_dead):
    """(c) Close missing sections of named lines.

    A dead end on a named way is joined to the nearest dead end of a way with the
    same name (within GAP_MAX_M) when the two are NOT already close on the network
    (network cost > 2.5 x straight distance + 2 km). This restores through-routes
    such as the WCML at Rugby or the Settle-Carlisle line, which the HOT export lacks.
    """
    n = len(nodes_xy)
    G = graph_matrix(edges, n)
    ends = raw_dead.drop_duplicates("node")
    new = []
    for nm, grp in ends.groupby("name"):
        if len(grp) < 2:
            continue
        nd = grp.node.to_numpy()
        tr = cKDTree(nodes_xy[nd])
        k = min(len(nd), 8)
        d, j = tr.query(nodes_xy[nd], k=k, distance_upper_bound=GAP_MAX_M)
        d = np.atleast_2d(d); j = np.atleast_2d(j)
        for a_i in range(len(nd)):
            cands = [(d[a_i, c], nd[j[a_i, c]]) for c in range(1, k) if np.isfinite(d[a_i, c]) and d[a_i, c] > 50]
            if not cands:
                continue
            u = nd[a_i]
            lim = 2.5 * max(c[0] for c in cands) + 2000
            dist = dijkstra(G, directed=False, indices=u, limit=lim)
            for dd, v in cands:
                if dist[v] > 2.5 * dd + 2000:
                    new.append((min(u, v), max(u, v), dd, nm))
                    break
    gaps = pd.DataFrame(new, columns=["u", "v", "length_m", "name"]).drop_duplicates(["u", "v"])
    if len(gaps):
        g = shapely.linestrings(np.stack([nodes_xy[gaps.u], nodes_xy[gaps.v]], 1))
        gaps = gaps.assign(way=-1, named=True, kind="gap", geometry=g, cost_m=gaps.length_m * GAP_PENALTY)
        edges = pd.concat([edges, gaps[edges.columns]], ignore_index=True)
    print(f"(c) named-line gaps closed: {len(gaps)}; total {gaps.length_m.sum()/1e3 if len(gaps) else 0:,.1f} km")
    return edges


# Central London stations joined by Underground/Elizabeth-line style transfer links,
# so cross-London journeys use a terminal plus the Tube rather than orbital rail lines.
CENTRAL = ["WAT", "WAE", "VXH", "VIC", "CHX", "LBG", "CST", "BFR", "CTK", "ZFD", "MOG", "OLD", "LST", "FST",
           "EUS", "STP", "KGX", "MYB", "PAD", "TCR", "BDS", "EPH", "ZLW", "SRA", "CWX", "HHY"]
TUBE_MAX_M = 8000.0
TUBE_FACTOR = 1.3
TUBE_PENALTY_M = 3000.0


def add_tube_links(nodes_xy, edges, st_nodes):
    sn = st_nodes.set_index("crs")
    c = [x for x in CENTRAL if x in sn.index]
    nd = sn.loc[c, "node"].to_numpy()
    rows = []
    for a in range(len(nd)):
        for b in range(a + 1, len(nd)):
            dd = float(np.hypot(*(nodes_xy[nd[a]] - nodes_xy[nd[b]])))
            if 0 < dd <= TUBE_MAX_M:
                rows.append((nd[a], nd[b], dd))
    t = pd.DataFrame(rows, columns=["u", "v", "length_m"])
    t = t.assign(way=-1, named=False, name="transfer (Underground)", kind="tube",
                 geometry=shapely.linestrings(np.stack([nodes_xy[t.u], nodes_xy[t.v]], 1)),
                 cost_m=t.length_m * TUBE_FACTOR + TUBE_PENALTY_M)
    print(f"(d) central London transfer links: {len(t)}")
    return pd.concat([edges, t[edges.columns]], ignore_index=True)


def main():
    nodes_xy, edges, st_nodes, st, raw_dead = build_graph()
    n = len(nodes_xy)
    edges = close_named_gaps(nodes_xy, edges, raw_dead)
    edges = add_tube_links(nodes_xy, edges, st_nodes)
    G = graph_matrix(edges, n)
    lab = connected_components(G, directed=False)[1]
    main_c = np.bincount(lab).argmax()
    st_nodes["in_main_component"] = lab[st_nodes.node] == main_c
    print(f"stations outside main component: {(~st_nodes.in_main_component).sum()} ; snap > 1 km: {(st_nodes.snap_m>1000).sum()}")
    print(st_nodes[(~st_nodes.in_main_component) | (st_nodes.snap_m > 1000)].merge(st[["crs", "name"]], on="crs").to_string())

    np.save(C.WORK / "net_nodes.npy", nodes_xy)
    gpd.GeoDataFrame(edges, geometry="geometry", crs=C.CRS_EPSG).to_parquet(C.WORK / "net_edges.parquet")
    st_nodes.to_csv(C.WORK / "station_nodes.csv", index=False)

    t0 = time.time()
    src = st_nodes.node.to_numpy(); S = len(src)
    skim = np.empty((S, S))
    for k in range(0, S, 250):
        D = dijkstra(G, directed=False, indices=src[k:k + 250])
        skim[k:k + 250] = D[:, src] / 1000.0
    acc = st_nodes.snap_m.to_numpy() / 1000.0
    skim = skim + acc[:, None] + acc[None, :]
    np.fill_diagonal(skim, 0.0)
    np.save(C.WORK / "skim_cost_km.npy", skim)
    print(f"skim done ({time.time()-t0:.0f}s); finite share {np.isfinite(skim).mean():.4f}")


if __name__ == "__main__":
    main()
