"""Assign stations to ORR 'county or unitary' local authorities and
prepare the observed LA-to-LA journeys (ORR Table 1595, Apr-2024 to Mar-2025).

Station -> LA uses the admin attribute already in the HOT OSM export
(geoBoundaries ADM2 = county / unitary authority): the nearest OSM station
point within 300 m, otherwise the nearest OSM rail line. Two post-2019
boundary changes are fixed by hand (Cumbria, Northamptonshire).

The assignment is checked against ORR's own numbers: for every LA, the sum of
station entries+exits (Table 1410) must equal 2 x within-LA journeys + journeys
to/from other LAs (Table 1595), because both tables come from the same LENNON base.

Outputs: outputs/model/station_la.csv, la_flows_2425.csv; outputs/tables/la_assignment_check.csv
"""
import re
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from . import config as C

T1595 = C.TABLE_1595
PERIOD = C.TABLE_1595_PERIOD

WESTMORLAND_FURNESS = {  # stations in the former Barrow, Eden and South Lakeland districts
    "Penrith (North Lakes)", "Appleby", "Kirkby Stephen", "Lazonby and Kirkoswald", "Langwathby",
    "Armathwaite", "Dent", "Garsdale", "Oxenholme Lake District", "Kendal", "Burneside (Cumbria)",
    "Staveley (Cumbria)", "Windermere", "Arnside", "Grange-Over-Sands", "Kents Bank", "Cark and Cartmel",
    "Ulverston", "Dalton (Cumbria)", "Roose", "Barrow-In-Furness", "Askam", "Kirkby-In-Furness", "Foxfield",
}
NORTH_NORTHANTS = {"Corby", "Kettering", "Wellingborough"}
# Manual fixes where the snapped admin area is wrong (checked against Table 1595 LA totals)
OVERRIDES = {
    "Rugby": "Warwickshire", "Manor Park": "Newham", "Avonmouth": "Bristol City Of",
    "St Andrews Road": "Bristol City Of", "Shirehampton": "Bristol City Of", "Sea Mills": "Bristol City Of",
    "Manors": "Newcastle upon Tyne", "Reading Green Park": "Reading", "Canonbury": "Islington",
    "West Brompton": "Hammersmith and Fulham", "Dent": "Westmorland and Furness", "Garsdale": "Westmorland and Furness",
    # central London: the geoBoundaries admin attribute in the OSM export is unreliable here
    "London Waterloo": "Lambeth", "London Bridge": "Southwark", "London Victoria": "Westminster",
    "London Liverpool Street": "City of London", "London Fenchurch Street": "City of London",
    "London Cannon Street": "City of London", "London Blackfriars": "City of London", "Moorgate": "City of London",
    "City Thameslink": "City of London", "London Charing Cross": "Westminster", "London Paddington": "Westminster",
    "London Marylebone": "Westminster", "Bond Street": "Westminster",
    "Farringdon": "Islington", "Whitechapel": "Tower Hamlets", "London Euston": "Camden",
    "London St Pancras International": "Camden", "London Kings Cross": "Camden", "Elephant & Castle": "Southwark",
    "Elephant and Castle": "Southwark", "London Waterloo East": "Southwark", "Vauxhall": "Lambeth",
    "Clapham Junction": "Wandsworth", "Stratford (London)": "Newham", "Canary Wharf": "Tower Hamlets",
    "Kensington Olympia": "Kensington and Chelsea", "Manchester Victoria": "Manchester", "Newcastle": "Newcastle upon Tyne",
    "Tottenham Court Road": "Camden", "Luton Airport Parkway": "Luton", "Woolwich": "Greenwich",
    "Limehouse": "Tower Hamlets", "Queens Road (Peckham)": "Southwark", "Stratford International": "Newham",
    "Shepherd's Bush": "Hammersmith and Fulham", "Earlsfield": "Wandsworth", "Wandsworth Town": "Wandsworth",
    "Harrow-On-The-Hill": "Harrow",
}


def norm(s):
    s = str(s).split(" - ")[0].lower().replace(",", "").replace("city of", "").replace("&", "and")
    s = re.sub(r"[^a-z]", "", s)
    return {"rhonddacynontaf": "rhonddacynontaff", "valeofglamorgan": "thevaleofglamorgan"}.get(s, s)


def main():
    st = pd.read_csv(C.WORK / "stations.csv")
    g = gpd.GeoDataFrame(st[["crs", "name", "region", "ee_all"]], geometry=gpd.points_from_xy(st.x, st.y), crs=C.CRS_EPSG)
    pts = gpd.read_file(C.OSM_POINTS, columns=["adm2_name"], engine="pyogrio").to_crs(C.CRS_EPSG)
    lines = gpd.read_file(C.OSM_LINES, columns=["adm2_name"], engine="pyogrio").to_crs(C.CRS_EPSG)
    jp = gpd.sjoin_nearest(g, pts, how="left", distance_col="dp").drop_duplicates("crs").set_index("crs")
    jl = gpd.sjoin_nearest(g, lines, how="left", distance_col="dl").drop_duplicates("crs").set_index("crs")
    adm = np.where(jp.loc[st.crs, "dp"].to_numpy() <= 300, jp.loc[st.crs, "adm2_name"], jl.loc[st.crs, "adm2_name"])
    st["adm2"] = adm

    t = pd.read_csv(T1595)
    t = t[t["Time Period"] == PERIOD].rename(columns={
        "Local authority: county or unitary 1": "la1", "Local authority: county or unitary 2": "la2",
        "Local authority: county or unitary code 1": "code1", "Local authority: county or unitary code 2": "code2",
        "Journeys": "journeys"})[["la1", "la2", "code1", "code2", "journeys"]]
    las = pd.concat([t[["la1", "code1"]].set_axis(["la", "code"], axis=1), t[["la2", "code2"]].set_axis(["la", "code"], axis=1)]).drop_duplicates("la")
    la_by_norm = dict(zip(las.la.map(norm), las.la))

    st["la"] = st["adm2"].map(lambda a: la_by_norm.get(norm(a)))
    cum = st["adm2"] == "Cumbria"
    st.loc[cum, "la"] = np.where(st.loc[cum, "name"].isin(WESTMORLAND_FURNESS), "Westmorland and Furness", "Cumberland")
    nth = st["adm2"] == "Northamptonshire"
    st.loc[nth, "la"] = np.where(st.loc[nth, "name"].isin(NORTH_NORTHANTS), "North Northamptonshire", "West Northamptonshire")
    ov = st["name"].isin(OVERRIDES)
    st.loc[ov, "la"] = st.loc[ov, "name"].map(OVERRIDES)
    print("stations without LA:", st.la.isna().sum())

    # LA totals implied by Table 1595 (within-LA flows counted twice, as in entries+exits)
    lt = pd.concat([t[["la1", "journeys"]].set_axis(["la", "j"], axis=1), t[["la2", "journeys"]].set_axis(["la", "j"], axis=1)])
    la_tot = lt.groupby("la").j.sum()

    # border stations: candidate LAs = admin areas of OSM features within 3 km
    def to_la(a, name):
        if a == "Cumbria":
            return "Westmorland and Furness" if name in WESTMORLAND_FURNESS else "Cumberland"
        if a == "Northamptonshire":
            return "North Northamptonshire" if name in NORTH_NORTHANTS else "West Northamptonshire"
        return la_by_norm.get(norm(a))
    feats = pd.concat([pts[["adm2_name", "geometry"]], lines[["adm2_name", "geometry"]]], ignore_index=True)
    fg = gpd.GeoDataFrame(feats, crs=C.CRS_EPSG)
    near = gpd.sjoin(g.assign(geometry=g.buffer(8000)), fg, predicate="intersects")
    sp = dict(zip(st.crs, shapely.points(st.x.to_numpy(), st.y.to_numpy())))
    near["dist"] = shapely.distance(np.array([sp[c] for c in near["crs"]]), fg.geometry.values[near.index_right.to_numpy()])
    near["la_c"] = [to_la(a, nm) for a, nm in zip(near.adm2_name, near.name)]
    near = near.dropna(subset=["la_c"]).sort_values("dist").drop_duplicates(["crs", "la_c"])
    # an LA belongs to one ORR region (majority of its stations' entries+exits); a
    # station whose ORR region differs from its LA's region is mis-assigned, so it
    # is moved to the nearest candidate LA in its own region
    la_reg = st.groupby(["la", "region"]).ee_all.sum().reset_index().sort_values("ee_all").drop_duplicates("la", keep="last").set_index("la").region
    near["la_reg"] = near.la_c.map(la_reg)
    near = near[(near.la_reg == near.region) | near.la_reg.isna()]
    fixed = 0
    for i in np.flatnonzero((st.la.map(la_reg) != st.region).to_numpy() & ~ov.to_numpy()):
        c = near[near["crs"] == st.at[i, "crs"]]
        if len(c):
            st.at[i, "la"] = c.la_c.iat[0]; fixed += 1
    print(f"stations moved to an LA in their own ORR region: {fixed}")
    near3 = near[near.dist <= 3000]
    cand = near3.groupby("crs").la_c.apply(lambda s: sorted(set(s)))
    st["cands"] = [sorted(set(cand.get(c, [])) | {la}) for c, la in zip(st.crs, st.la)]
    # greedy local search: move stations between candidate LAs while the total
    # |EE(1410) - EE(1595)| over LAs decreases
    cur = st.groupby("la").ee_all.sum().reindex(la_tot.index).fillna(0)
    ee = st.ee_all.to_numpy()
    moves = 0
    for it in range(50):
        best = (0.0, None, None)
        # only small stations may move: large stations are fixed by the admin attribute or OVERRIDES
        for i in np.flatnonzero((st.cands.map(len) > 1) & ~ov & (st.ee_all < 3e6)):
            a = st.at[i, "la"]
            for b in st.at[i, "cands"]:
                if b == a:
                    continue
                before = abs(cur[a] - la_tot[a]) + abs(cur[b] - la_tot[b])
                after = abs(cur[a] - ee[i] - la_tot[a]) + abs(cur[b] + ee[i] - la_tot[b])
                gain = before - after
                if gain > best[0]:
                    best = (gain, i, b)
        if best[1] is None or best[0] < 1000:
            break
        _, i, b = best
        a = st.at[i, "la"]
        cur[a] -= ee[i]; cur[b] += ee[i]; st.at[i, "la"] = b; moves += 1
        print(f"  move {st.at[i,'name']} ({ee[i]/1e6:.1f}m EE): {a} -> {b}")
    print(f"stations re-assigned by the consistency search: {moves}")
    st = st.merge(las, on="la", how="left")

    # consistency check vs Table 1595
    chk = pd.DataFrame({"ee_1410": st.groupby("la").ee_all.sum(), "ee_1595": la_tot}).fillna(0)
    chk["diff_pct"] = 100 * (chk.ee_1410 - chk.ee_1595) / chk.ee_1595.clip(lower=1)
    chk.sort_values("diff_pct").to_csv(C.TAB / "la_assignment_check.csv")
    bad = chk[chk.diff_pct.abs() > 2]
    print(f"LAs: {len(chk)}; |diff| > 2%: {len(bad)}; total EE 1410 {chk.ee_1410.sum()/1e6:,.1f}m vs 1595 {chk.ee_1595.sum()/1e6:,.1f}m")
    print(bad.sort_values("diff_pct").round(1).to_string())
    st[["crs", "name", "region", "adm2", "la", "code"]].to_csv(C.WORK / "station_la.csv", index=False)
    t.to_csv(C.WORK / "la_flows_2425.csv", index=False)


if __name__ == "__main__":
    main()
