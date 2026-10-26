"""Configuration for the railflow model.

Paths
-----
Inputs are read from the data directory and everything the model produces is
written to the output directory. Both default to ``./data`` and ``./outputs``
under the current working directory and can be changed with the environment
variables ``RAILFLOW_DATA_DIR`` and ``RAILFLOW_OUTPUT_DIR`` (the command-line
interface sets them from ``--data`` and ``--out``).

Every modelling assumption that is not read from a data file is set here, so
it can be reviewed, changed and versioned in one place.
"""
import os
from pathlib import Path

MODEL_NAME = "railflow"
MODEL_VERSION = "0.1.0"
BASE_YEAR = "2024-25"            # ORR financial year of the demand data

DATA = Path(os.environ.get("RAILFLOW_DATA_DIR", "data")).resolve()
OUT = Path(os.environ.get("RAILFLOW_OUTPUT_DIR", "outputs")).resolve()
WORK = OUT / "model"             # model files used by downstream projects (see railflow.api)
FIG = OUT / "figures"
TAB = OUT / "tables"
ROOT = OUT                       # kept for compatibility with older scripts
for p in (OUT, WORK, FIG, TAB):
    p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- inputs
TABLE_1410 = DATA / "table-1410-passenger-entries-and-exits-and-interchanges-by-station.ods"
TABLE_1595 = DATA / "table-1595-passenger-journeys-between-local-authorities.csv"
TABLE_1595_PERIOD = "Apr 2024 to Mar 2025"
OSM_LINES = DATA / "osm" / "railways_lines.shp"
OSM_POINTS = DATA / "osm" / "railways_points.shp"
STATIONS_JSON = DATA / "ext" / "stations.json"           # davwheat/uk-railway-stations (CRS, lat/lon)
STATIONS_CSV_ALT = DATA / "ext" / "uk-train-stations.csv"  # ellcom/UK-Train-Station-Locations (fallback)

# ------------------------------------------------- average weekday factors
# ORR Table 1410 gives annual entries+exits by ticket type.
# Average weekday (AWD) = annual / divisor, applied by ticket type:
#   * Season-ticket journeys are commuting journeys made on working weekdays,
#     so they are spread over the ~252 working weekdays in the year.
#   * Full and reduced-price (ordinary) journeys are spread over the whole year
#     with a day-of-week index (weekday = 1.0). Post-pandemic weekend travel has
#     recovered more strongly than weekday travel (Transport Scotland; TfL
#     Travel in London 2024), so Saturday is set close to a weekday.
# Replace with LENNON day-of-week factors when available (see the technical document).
WORKING_WEEKDAYS = 252
SAT_INDEX = 0.90
SUN_INDEX = 0.60
N_SATURDAYS = 52
N_SUNDAYS_BH = 52 + 8
SEASON_DIVISOR = WORKING_WEEKDAYS
ORDINARY_DIVISOR = WORKING_WEEKDAYS + SAT_INDEX * N_SATURDAYS + SUN_INDEX * N_SUNDAYS_BH

# ---------------------------------------------------------------- regions
REGIONS = [
    "North East", "North West", "Yorkshire and The Humber", "East Midlands",
    "West Midlands", "East of England", "London", "South East", "South West",
    "Wales", "Scotland",
]
REGION_SHORT = {
    "North East": "NE", "North West": "NW", "Yorkshire and The Humber": "YH",
    "East Midlands": "EM", "West Midlands": "WM", "East of England": "EE",
    "London": "LON", "South East": "SE", "South West": "SW", "Wales": "WAL",
    "Scotland": "SCO",
}
# The ETC 2018 RailWatch paper (Table 1) aggregated the regions to seven groups.
PAPER_GROUPS = {
    "North East": "Yorkshire & North", "North West": "Yorkshire & North",
    "Yorkshire and The Humber": "Yorkshire & North",
    "East Midlands": "English Midlands", "West Midlands": "English Midlands",
    "East of England": "East of England", "London": "London",
    "South East": "South of England", "South West": "South of England",
    "Wales": "Wales", "Scotland": "Scotland",
}
# Paper Table 1: average AM trip length (km) from MND, 2018 - kept for comparison only.
PAPER_TABLE1_KM = {
    ("Yorkshire & North", "int"): 63, ("English Midlands", "int"): 49,
    ("East of England", "int"): 57, ("London", "int"): 20,
    ("South of England", "int"): 68, ("Wales", "int"): 45, ("Scotland", "int"): 53,
    ("Yorkshire & North", "ext"): 183, ("English Midlands", "ext"): 219,
    ("East of England", "ext"): 110, ("London", "ext"): 134,
    ("South of England", "ext"): 117, ("Wales", "ext"): 177, ("Scotland", "ext"): 218,
}

# ORR published totals used for validation (2024-25).
ORR_WITHIN_SHARE_GB = 1084 / 1532
ORR_PKM_BN = 64.6
ORR_JOURNEYS_M = 1729.0

# --------------------------------------------------------------- network
CRS_EPSG = 27700                 # British National Grid (metres)
UNNAMED_WAY_PENALTY = 1.25       # unnamed OSM ways are mostly sidings, yards and depots
STATION_SNAP_MAX_M = 1500
MIN_DIST_KM = 1.0                # floor for very short distances in the deterrence functions

# Default map extents (BNG metres) for the standard figures.
LONDON_BBOX = (505000, 165000, 545000, 195000)
