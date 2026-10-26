# railflow input data

All inputs live in this folder (or in the folder given by `--data` / `RAILFLOW_DATA_DIR`).
File names are set in `railflow/config.py`.

| File | Source | Licence | Used for | SHA-256 (base year 2024-25) |
|---|---|---|---|---|
| `table-1410-passenger-entries-and-exits-and-interchanges-by-station.ods` | ORR, [Estimates of station usage](https://dataportal.orr.gov.uk/statistics/usage/estimates-of-station-usage/), Table 1410, April 2024 – March 2025 | Open Government Licence v3.0 | Trip ends by ticket type, main flow per station, region | `8e1e5283…d39895` |
| `table-1595-passenger-journeys-between-local-authorities.csv` | ORR, [Regional rail usage](https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage/table-1595-passenger-journeys-between-local-authorities/), Table 1595 (CSV on request from ORR or exported from the ODS) | Open Government Licence v3.0 | Calibration targets, LA totals for Model B, validation | `4a2c80e2…732c810` |
| `ext/stations.json` | [davwheat/uk-railway-stations](https://github.com/davwheat/uk-railway-stations) | As stated in that repository | Station coordinates by CRS | `083f835c…82a88a2` |
| `ext/uk-train-stations.csv` | [ellcom/UK-Train-Station-Locations](https://github.com/ellcom/UK-Train-Station-Locations) | As stated in that repository | Second coordinate list (cross-check and fallback) | `e8d4afa8…fdcf74` |
| `osm/railways_lines.shp` (+ .dbf .shx .prj .cpg) and `osm/railways_points.*` | `hotosm_gbr_railways_osm_shp`: HOT export of OpenStreetMap made with [oex](https://github.com/osgeonepal/oex) 0.4.16 from the Geofabrik GBR extract, snapshot 2026-10-09 | Open Database Licence (ODbL) | Rail network, station-to-LA admin attribute | not committed (168 MB) |

Full checksums: run `sha256sum data/*.ods data/*.csv data/ext/*` and compare with `data/SHA256SUMS`.

## Annual refresh

ORR publishes station usage (Table 1410) in December and regional rail usage (Table 1595) around the same time.
For a new base year:

1. Replace both tables and update `TABLE_1410`, `TABLE_1595`, `TABLE_1595_PERIOD` and `BASE_YEAR` in `railflow/config.py`.
2. Check the ORR totals used for validation (`ORR_PKM_BN`, `ORR_JOURNEYS_M`, `ORR_WITHIN_SHARE_GB`) against the new passenger rail usage release.
3. Run `python -m railflow run --recalibrate`, then `python docs/build_docs.py`, and record the changes in the change log of the technical document.

## OSM network

The export is the `hotosm_gbr_railways_osm_shp` file set supplied with the SWR Service Recovery project.
Any OpenStreetMap railway extract with the same attributes (`name`, `adm1_name`, `adm2_name`) works;
a newer snapshot changes network repairs slightly, so re-run the whole model and compare validation results.
