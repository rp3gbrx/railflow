"""Sources for the railflow documents (technical document, applications note, sources page).

Each entry: title, by, where, url (or None for documents supplied with the project), use.
Groups are rendered in order and numbering continues across groups.
"""
import html

SOURCES = [
    ("Method references (supplied with the project)", [
        dict(title="Real-time estimation of train occupancies using mobile phone data (RailWatch)", by="Prince, R. and Perret, P., Citi Logik Ltd",
             where="European Transport Conference 2018, AET", url=None,
             use="Train Occupancy Model: trip-end model, gravity distribution with multiple region-level deterrence functions (Section 2.2, Table 1), schedule-based assignment (Section 2.3)."),
        dict(title="Estimating Parameters of Deterrence Functions in Synthetic Matrix Development (technical note)", by="Prince, R., AECOM",
             where="Technical note (PDF dated March 2022)", url=None,
             use="Calibration as non-linear least squares (Levenberg–Marquardt) of deterrence parameters against trip-length distributions."),
        dict(title="Calibrate_Synthetic_ParmsNew.R (version 1.4, multiple deterrence functions)", by="Prince, R.", where="R script, 2017", url=None,
             use="Log-normal deterrence form (dlnorm) and multi-segment calibration logic."),
    ]),
    ("Office of Rail and Road (ORR)", [
        dict(title="Table 1410: Passenger entries, exits and interchanges by station, April 2024 – March 2025", by="ORR",
             where="Estimates of station usage 2024-25 (statistical release)",
             url="https://dataportal.orr.gov.uk/media/msigcn24/station-usage-2024-25-statistical-release.pdf",
             use="Station trip ends by ticket type; main origin/destination flow per station; station region and facility owner."),
        dict(title="Table 1595: Passenger journeys between local authorities", by="ORR", where="Regional rail usage, April 2024 – March 2025",
             url="https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage/table-1595-passenger-journeys-between-local-authorities/",
             use="Observed trip-length distributions by region (calibration targets); LA-pair totals for Model B; validation."),
        dict(title="Table 1520: Regional passenger journeys between and within regions", by="ORR", where="Regional rail usage, April 2024 – March 2025",
             url="https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage/table-1520-regional-passenger-journeys-between-and-within-regions/",
             use="Cross-check of regional totals."),
        dict(title="Regional rail usage (data portal page)", by="ORR", where="Statistics, 2024-25", url="https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage",
             use="Within- and between-region journey totals (1,084m and 448m)."),
        dict(title="Passenger rail usage, January to March 2025 (statistical release)", by="ORR", where="PDF",
             url="https://dataportal.orr.gov.uk/media/zzlpyvq4/passenger-rail-usage-jan-mar-2025.pdf",
             use="GB 2024-25 totals: 1,729m journeys and 64.6bn passenger-km (validation)."),
        dict(title="Estimates of station usage: quality and methodology report", by="ORR", where="PDF",
             url="https://dataportal.orr.gov.uk/media/1917/station-usage-quality-and-methodology-report.pdf",
             use="How LENNON sales become journeys (season-ticket journey factors), the Origin-Destination Matrix (ODM), station groups, Travelcard and PTE infill; ODM availability on the Rail Data Marketplace."),
        dict(title="Freight rail usage and performance (data portal page)", by="ORR", where="Statistics, latest release April–June 2026",
             url="https://dataportal.orr.gov.uk/statistics/usage/freight-rail-usage-and-performance",
             use="Freight control totals for the roadmap (Table 1330 freight trains run, Table 1333 freight train km by operator)."),
    ]),
    ("Network and reference data", [
        dict(title="hotosm_gbr_railways_osm_shp (railways, OSM snapshot 2026-10-09)", by="Humanitarian OpenStreetMap Team export of OpenStreetMap; oex 0.4.16",
             where="ESRI Shapefile; Open Database Licence (ODbL)", url="https://github.com/osgeonepal/oex",
             use="Rail network for distances, assignment and maps; admin areas for station-to-LA mapping."),
        dict(title="uk-railway-stations (stations.json)", by="davwheat", where="GitHub", url="https://github.com/davwheat/uk-railway-stations",
             use="Station coordinates by CRS code."),
        dict(title="UK-Train-Station-Locations", by="ellcom", where="GitHub", url="https://github.com/ellcom/UK-Train-Station-Locations",
             use="Second set of station coordinates (cross-check and fallback)."),
        dict(title="network-rail-gis: track, reference line and organisational boundaries", by="Open Rail Data (Network Rail data, Open Government Licence)",
             where="GitHub; listed on DfT Find Transport Data", url="https://github.com/openraildata/network-rail-gis",
             use="Roadmap: replacement network with Engineer's Line References and Network Rail route boundaries."),
        dict(title="Track, reference line and organisational boundaries (dataset record)", by="DfT Find Transport Data", where="Web page",
             url="https://findtransportdata.dft.gov.uk/dataset/track,-reference-line-and-organisational-boundaries-182fe21f794",
             use="Licence (OGL) and quarterly update frequency of the Network Rail GIS data."),
        dict(title="SCHEDULE feed", by="Open Rail Data wiki (Network Rail open data feeds)", where="Web page",
             url="https://wiki.openraildata.com/index.php/SCHEDULE",
             use="Roadmap: timetable (CIF/JSON) for generalised costs and schedule-based assignment; separate FREIGHT schedule file (JSON)."),
        dict(title="About the Network Rail feeds", by="Open Rail Data wiki", where="Web page", url="https://wiki.openraildata.com/index.php/About_the_feeds",
             use="Roadmap: TRUST train movements and other feeds."),
        dict(title="Reference Data", by="Open Rail Data wiki", where="Web page", url="https://wiki.openraildata.com/index.php/Reference_Data",
             use="Meaning of TIPLOC, STANOX, CRS and NLC location codes."),
        dict(title="YA_Tiploc_List (tiplocs-merged-stanox.csv)", by="Jnction", where="GitHub; merges NaPTAN, CORPUS, BPLAN and other sources",
             url="https://github.com/Jnction/YA_Tiploc_List", use="Roadmap: locating TIPLOCs on the network to link timetables and TRUST data."),
        dict(title="Rail Origin Destination Matrix 2022-23 (TfSE Centre of Excellence data item)", by="Transport for the South East", where="Web page; data sourced from the Rail Data Marketplace",
             url="https://coe.transportforthesoutheast.org.uk/data-item/rail-origin-destination-matrix-2022-23",
             use="Evidence that station-to-station ODM extracts are obtainable for project use (roadmap item R1)."),
        dict(title="National Trip End Model (NTEM) version 8.0", by="Department for Transport", where="data.gov.uk dataset (core, high and low scenarios)",
             url="https://ckan.publishing.service.gov.uk/dataset/national-trip-end-model-ntem/resource/1a019027-77fe-497c-8a38-3ef1ef231393",
             use="Roadmap: time-period origin/destination factors and growth for scenarios, as used in the RailWatch trip-end model."),
    ]),
    ("Evidence for the average-weekday factors", [
        dict(title="Public use of transport – trends and patterns (Fair Fares Review, supporting paper one)", by="Transport Scotland", where="Web publication",
             url="https://www.transport.gov.scot/publication/public-transport-system-analysis-supporting-paper-one-fair-fares-review/public-use-of-transport-trends-and-patterns",
             use="Weekday rail at about 80% of pre-pandemic levels, with weekends recovering more strongly."),
        dict(title="Travel in London 2024: trends in public transport demand and operational performance", by="Transport for London", where="PDF",
             url="https://content.tfl.gov.uk/travel-in-london-2024-trends-in-public-transport-demand-and-operational-performance-acc.pdf",
             use="Day-of-week recovery pattern (Saturday and Sunday above weekdays)."),
    ]),
    ("Projects using the model (supplied as otherProjects)", [
        dict(title="Split Ticket Calculator (Confluence page)", by="AIIA project team", where="Confluence export, 2026", url=None,
             use="STC pipeline, Pewsey as a top split point, Weymouth–Melksham and Aldermaston–Betchworth examples."),
        dict(title="Flow Classification – Preliminary model (Confluence page)", by="AIIA project team", where="Confluence export, 2026", url=None,
             use="Five-cluster k-means of 15,072 PMS flows for London Overground and Greater Anglia; stated limitations (missing mileages, LENNON to be added)."),
        dict(title="T3 & Cancellation Prediction Analysis (Confluence page)", by="AIIA project team", where="Confluence export, 2026", url=None,
             use="Route-period T3 and cancellation prediction (XGBoost, SARIMAX); PfPI definition."),
        dict(title="SWR Service Recovery POC (Confluence pages and FTS Success Tracker)", by="GBRX project team / South Western Railway", where="Project folder, Oct 2026", url=None,
             use="First application of the model (see the swr-service-recovery-flows repository)."),
    ]),
    ("Software", [
        dict(title="Python: NumPy, pandas, SciPy, GeoPandas, Shapely, pyogrio, pyarrow, Numba, statsmodels, Matplotlib", by="Open-source projects", where="Python packages",
             url=None, use="Modelling, assignment, statistics and figures."),
        dict(title="pandoc, Beautiful Soup, lxml", by="Open-source projects", where="Document tools", url=None,
             use="Confluence storage format, Word and Markdown versions of the documents."),
    ]),
]


def html_list():
    """HTML <h3>/<ol> blocks (numbering continues across groups)."""
    out, n = [], 0
    for grp, items in SOURCES:
        out.append(f"<h3>{html.escape(grp)}</h3>")
        out.append(f'<ol start="{n + 1}">')
        for s in items:
            n += 1
            t = html.escape(s["title"])
            t = f'<a href="{html.escape(s["url"])}">{t}</a>' if s["url"] else f"<i>{t}</i>"
            url_txt = f'<br><span class="url">{html.escape(s["url"])}</span>' if s["url"] else ""
            out.append(f'<li>{t}. {html.escape(s["by"])}. {html.escape(s["where"])}.{url_txt}'
                       f'<br><span class="use">Used for: {html.escape(s["use"])}</span></li>')
        out.append("</ol>")
    return "\n".join(out)
