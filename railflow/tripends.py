"""Station trip ends for an average weekday.

Reads ORR Table 1410 (Apr-2024 to Mar-2025), attaches coordinates and the
government region, converts annual entries+exits to an average weekday by
ticket type, and splits into origins / destinations.

Output: outputs/model/stations.csv
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from . import config as C


def load_1410() -> pd.DataFrame:
    df = pd.read_excel(C.TABLE_1410, sheet_name="1410_Entries_Exits_Interchanges", header=3, engine="odf")
    df.columns = [c.strip() for c in df.columns]
    ren = {
        "Station name": "name",
        "Entries and exits: Full price tickets": "ee_full",
        "Entries and exits: Reduced price tickets": "ee_reduced",
        "Entries and exits:Season tickets": "ee_season",
        "Entries and exits:All tickets": "ee_all",
        "Entries and exits:Rank": "rank",
        "Interchanges": "interchanges",
        "Main origin or destination station": "main_od_name",
        "Number of journeys to or from main origin or destination station": "main_od_journeys",
        "National Location Code (NLC)": "nlc",
        "Three Letter Code(TLC)": "crs",
        "Region": "region",
        "Station facility owner": "sfo",
        "Station group": "station_group",
    }
    df = df.rename(columns=ren)[list(ren.values())]
    for c in ["ee_full", "ee_reduced", "ee_season", "ee_all", "interchanges", "main_od_journeys"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["crs"] = df["crs"].astype(str).str.strip()
    return df


def attach_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    dv = pd.DataFrame(json.load(open(C.STATIONS_JSON)))[["crsCode", "lat", "long"]]
    dv.columns = ["crs", "lat", "lon"]
    alt = pd.read_csv(C.STATIONS_CSV_ALT).rename(columns={"station_code": "crs", "latitude": "lat_alt", "longitude": "lon_alt"})
    df = df.merge(dv, on="crs", how="left").merge(alt[["crs", "lat_alt", "lon_alt"]], on="crs", how="left")
    miss = df["lat"].isna()
    df.loc[miss, "lat"] = df.loc[miss, "lat_alt"]
    df.loc[miss, "lon"] = df.loc[miss, "lon_alt"]
    df["coord_source"] = np.where(miss, "ellcom", "davwheat")
    # flag disagreements between the two sources (> 2 km) for review
    g1 = gpd.GeoSeries(gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(C.CRS_EPSG)
    g2 = gpd.GeoSeries(gpd.points_from_xy(df.lon_alt, df.lat_alt), crs=4326).to_crs(C.CRS_EPSG)
    df["coord_disagree_m"] = g1.distance(g2).round(0)
    df["x"], df["y"] = g1.x.values, g1.y.values
    return df.drop(columns=["lat_alt", "lon_alt"])


def weekday_trip_ends(df: pd.DataFrame) -> pd.DataFrame:
    ordinary = df["ee_full"] + df["ee_reduced"]
    # Some stations report only an all-ticket total; treat any residual as ordinary.
    resid = (df["ee_all"] - ordinary - df["ee_season"]).clip(lower=0)
    ordinary = ordinary + resid
    df["ee_awd"] = ordinary / C.ORDINARY_DIVISOR + df["ee_season"] / C.SEASON_DIVISOR
    df["season_share"] = np.where(df["ee_all"] > 0, df["ee_season"] / df["ee_all"], 0)
    df["annualisation_factor"] = np.where(df["ee_awd"] > 0, df["ee_all"] / df["ee_awd"], np.nan)
    # Each journey is counted once as an entry and once as an exit, so an
    # all-day matrix has origins = destinations = half of entries+exits.
    df["O_awd"] = df["ee_awd"] / 2.0
    df["D_awd"] = df["ee_awd"] / 2.0
    return df


def main():
    df = load_1410()
    df = attach_coordinates(df)
    df = weekday_trip_ends(df)
    # map the 'main origin/destination' station name to its CRS (used later for validation)
    name2crs = dict(zip(df["name"], df["crs"]))
    df["main_od_crs"] = df["main_od_name"].map(name2crs)
    df["region_short"] = df["region"].map(C.REGION_SHORT)
    df["paper_group"] = df["region"].map(C.PAPER_GROUPS)
    df = df[df["ee_all"] > 0].reset_index(drop=True)
    df.to_csv(C.WORK / "stations.csv", index=False)

    tot_ann = df["ee_all"].sum() / 2
    tot_awd = df["ee_awd"].sum() / 2
    print(f"stations with demand: {len(df)}")
    print(f"annual journeys (EE/2): {tot_ann/1e6:,.1f}m ; average weekday journeys: {tot_awd/1e6:,.3f}m ; implied factor {tot_ann/tot_awd:,.1f}")
    print(f"main-OD names unmatched to a CRS: {df['main_od_crs'].isna().sum()}")
    print(f"coordinate sources: {df['coord_source'].value_counts().to_dict()} ; >2km disagreements: {(df['coord_disagree_m']>2000).sum()}")
    reg = df.groupby("region").agg(stations=("crs", "size"), awd_journeys=("O_awd", "sum"))
    print(reg.sort_values("awd_journeys", ascending=False).round(0))


if __name__ == "__main__":
    main()
