# railflow sources

Every source used to build, document and apply the model. Generated from `docs/sources.py` on 25 October 2026.

Documents supplied with the project have no public link and are shown in italics. All other entries link to the source.

### Method references (supplied with the project)

1.  *Real-time estimation of train occupancies using mobile phone data (RailWatch)*. Prince, R. and Perret, P., Citi Logik Ltd. European Transport Conference 2018, AET.  
    <span class="use">Used for: Train Occupancy Model: trip-end model, gravity distribution with multiple region-level deterrence functions (Section 2.2, Table 1), schedule-based assignment (Section 2.3).</span>
2.  *Estimating Parameters of Deterrence Functions in Synthetic Matrix Development (technical note)*. Prince, R., AECOM. Technical note (Technical note related to: https://aetransport.org/public/downloads/Ss_zA/5533-59d12d0dea196.pdf ).  
    <span class="use">Used for: Calibration as non-linear least squares (Levenberg–Marquardt) of deterrence parameters against trip-length distributions.</span>
3.  *Calibrate_Synthetic_ParmsNew.R (code related to: Technical note related to: https://aetransport.org/public/downloads/Ss_zA/5533-59d12d0dea196.pdf )*. Prince, R.. R script, 2017.  
    <span class="use">Used for: Log-normal deterrence form (dlnorm) and multi-segment calibration logic.</span>

### Office of Rail and Road (ORR)

4.  [Table 1410: Passenger entries, exits and interchanges by station, April 2024 – March 2025](https://dataportal.orr.gov.uk/media/msigcn24/station-usage-2024-25-statistical-release.pdf). ORR. Estimates of station usage 2024-25 (statistical release).  
    <span class="url">https://dataportal.orr.gov.uk/media/msigcn24/station-usage-2024-25-statistical-release.pdf</span>  
    <span class="use">Used for: Station trip ends by ticket type; main origin/destination flow per station; station region and facility owner.</span>
5.  [Table 1595: Passenger journeys between local authorities](https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage/table-1595-passenger-journeys-between-local-authorities/). ORR. Regional rail usage, April 2024 – March 2025.  
    <span class="url">https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage/table-1595-passenger-journeys-between-local-authorities/</span>  
    <span class="use">Used for: Observed trip-length distributions by region (calibration targets); LA-pair totals for Model B; validation.</span>
6.  [Table 1520: Regional passenger journeys between and within regions](https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage/table-1520-regional-passenger-journeys-between-and-within-regions/). ORR. Regional rail usage, April 2024 – March 2025.  
    <span class="url">https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage/table-1520-regional-passenger-journeys-between-and-within-regions/</span>  
    <span class="use">Used for: Cross-check of regional totals.</span>
7.  [Regional rail usage (data portal page)](https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage). ORR. Statistics, 2024-25.  
    <span class="url">https://dataportal.orr.gov.uk/statistics/usage/regional-rail-usage</span>  
    <span class="use">Used for: Within- and between-region journey totals (1,084m and 448m).</span>
8.  [Passenger rail usage, January to March 2025 (statistical release)](https://dataportal.orr.gov.uk/media/zzlpyvq4/passenger-rail-usage-jan-mar-2025.pdf). ORR. PDF.  
    <span class="url">https://dataportal.orr.gov.uk/media/zzlpyvq4/passenger-rail-usage-jan-mar-2025.pdf</span>  
    <span class="use">Used for: GB 2024-25 totals: 1,729m journeys and 64.6bn passenger-km (validation).</span>
9.  [Estimates of station usage: quality and methodology report](https://dataportal.orr.gov.uk/media/1917/station-usage-quality-and-methodology-report.pdf). ORR. PDF.  
    <span class="url">https://dataportal.orr.gov.uk/media/1917/station-usage-quality-and-methodology-report.pdf</span>  
    <span class="use">Used for: How LENNON sales become journeys (season-ticket journey factors), the Origin-Destination Matrix (ODM), station groups, Travelcard and PTE infill; ODM availability on the Rail Data Marketplace.</span>
10. [Freight rail usage and performance (data portal page)](https://dataportal.orr.gov.uk/statistics/usage/freight-rail-usage-and-performance). ORR. Statistics, latest release April–June 2026.  
    <span class="url">https://dataportal.orr.gov.uk/statistics/usage/freight-rail-usage-and-performance</span>  
    <span class="use">Used for: Freight control totals for the roadmap (Table 1330 freight trains run, Table 1333 freight train km by operator).</span>

### Network and reference data

11. [hotosm_gbr_railways_osm_shp (railways, OSM snapshot 2026-10-09)](https://github.com/osgeonepal/oex). Humanitarian OpenStreetMap Team export of OpenStreetMap; oex 0.4.16. ESRI Shapefile; Open Database Licence (ODbL).  
    <span class="url">https://github.com/osgeonepal/oex</span>  
    <span class="use">Used for: Rail network for distances, assignment and maps; admin areas for station-to-LA mapping.</span>
12. [uk-railway-stations (stations.json)](https://github.com/davwheat/uk-railway-stations). davwheat. GitHub.  
    <span class="url">https://github.com/davwheat/uk-railway-stations</span>  
    <span class="use">Used for: Station coordinates by CRS code.</span>
13. [UK-Train-Station-Locations](https://github.com/ellcom/UK-Train-Station-Locations). ellcom. GitHub.  
    <span class="url">https://github.com/ellcom/UK-Train-Station-Locations</span>  
    <span class="use">Used for: Second set of station coordinates (cross-check and fallback).</span>
14. [network-rail-gis: track, reference line and organisational boundaries](https://github.com/openraildata/network-rail-gis). Open Rail Data (Network Rail data, Open Government Licence). GitHub; listed on DfT Find Transport Data.  
    <span class="url">https://github.com/openraildata/network-rail-gis</span>  
    <span class="use">Used for: Roadmap: replacement network with Engineer's Line References and Network Rail route boundaries.</span>
15. [Track, reference line and organisational boundaries (dataset record)](https://findtransportdata.dft.gov.uk/dataset/track,-reference-line-and-organisational-boundaries-182fe21f794). DfT Find Transport Data. Web page.  
    <span class="url">https://findtransportdata.dft.gov.uk/dataset/track,-reference-line-and-organisational-boundaries-182fe21f794</span>  
    <span class="use">Used for: Licence (OGL) and quarterly update frequency of the Network Rail GIS data.</span>
16. [SCHEDULE feed](https://wiki.openraildata.com/index.php/SCHEDULE). Open Rail Data wiki (Network Rail open data feeds). Web page.  
    <span class="url">https://wiki.openraildata.com/index.php/SCHEDULE</span>  
    <span class="use">Used for: Roadmap: timetable (CIF/JSON) for generalised costs and schedule-based assignment; separate FREIGHT schedule file (JSON).</span>
17. [About the Network Rail feeds](https://wiki.openraildata.com/index.php/About_the_feeds). Open Rail Data wiki. Web page.  
    <span class="url">https://wiki.openraildata.com/index.php/About_the_feeds</span>  
    <span class="use">Used for: Roadmap: TRUST train movements and other feeds.</span>
18. [Reference Data](https://wiki.openraildata.com/index.php/Reference_Data). Open Rail Data wiki. Web page.  
    <span class="url">https://wiki.openraildata.com/index.php/Reference_Data</span>  
    <span class="use">Used for: Meaning of TIPLOC, STANOX, CRS and NLC location codes.</span>
19. [YA_Tiploc_List (tiplocs-merged-stanox.csv)](https://github.com/Jnction/YA_Tiploc_List). Jnction. GitHub; merges NaPTAN, CORPUS, BPLAN and other sources.  
    <span class="url">https://github.com/Jnction/YA_Tiploc_List</span>  
    <span class="use">Used for: Roadmap: locating TIPLOCs on the network to link timetables and TRUST data.</span>
20. [Rail Origin Destination Matrix 2022-23 (TfSE Centre of Excellence data item)](https://coe.transportforthesoutheast.org.uk/data-item/rail-origin-destination-matrix-2022-23). Transport for the South East. Web page; data sourced from the Rail Data Marketplace.  
    <span class="url">https://coe.transportforthesoutheast.org.uk/data-item/rail-origin-destination-matrix-2022-23</span>  
    <span class="use">Used for: Evidence that station-to-station ODM extracts are obtainable for project use (roadmap item R1).</span>
21. [National Trip End Model (NTEM) version 8.0](https://ckan.publishing.service.gov.uk/dataset/national-trip-end-model-ntem/resource/1a019027-77fe-497c-8a38-3ef1ef231393). Department for Transport. data.gov.uk dataset (core, high and low scenarios).  
    <span class="url">https://ckan.publishing.service.gov.uk/dataset/national-trip-end-model-ntem/resource/1a019027-77fe-497c-8a38-3ef1ef231393</span>  
    <span class="use">Used for: Roadmap: time-period origin/destination factors and growth for scenarios, as used in the RailWatch trip-end model.</span>

### Evidence for the average-weekday factors

22. [Public use of transport – trends and patterns (Fair Fares Review, supporting paper one)](https://www.transport.gov.scot/publication/public-transport-system-analysis-supporting-paper-one-fair-fares-review/public-use-of-transport-trends-and-patterns). Transport Scotland. Web publication.  
    <span class="url">https://www.transport.gov.scot/publication/public-transport-system-analysis-supporting-paper-one-fair-fares-review/public-use-of-transport-trends-and-patterns</span>  
    <span class="use">Used for: Weekday rail at about 80% of pre-pandemic levels, with weekends recovering more strongly.</span>
23. [Travel in London 2024: trends in public transport demand and operational performance](https://content.tfl.gov.uk/travel-in-london-2024-trends-in-public-transport-demand-and-operational-performance-acc.pdf). Transport for London. PDF.  
    <span class="url">https://content.tfl.gov.uk/travel-in-london-2024-trends-in-public-transport-demand-and-operational-performance-acc.pdf</span>  
    <span class="use">Used for: Day-of-week recovery pattern (Saturday and Sunday above weekdays).</span>

### Projects using the model (supplied as otherProjects)

24. *Split Ticket Calculator (Confluence page)*. AIIA project team. Confluence export, 2026.  
    <span class="use">Used for: STC pipeline, Pewsey as a top split point, Weymouth–Melksham and Aldermaston–Betchworth examples.</span>
25. *Flow Classification – Preliminary model (Confluence page)*. AIIA project team. Confluence export, 2026.  
    <span class="use">Used for: Five-cluster k-means of 15,072 PMS flows for London Overground and Greater Anglia; stated limitations (missing mileages, LENNON to be added).</span>
26. *T3 & Cancellation Prediction Analysis (Confluence page)*. AIIA project team. Confluence export, 2026.  
    <span class="use">Used for: Route-period T3 and cancellation prediction (XGBoost, SARIMAX); PfPI definition.</span>
27. *SWR Service Recovery POC (Confluence pages and FTS Success Tracker)*. GBRX project team / South Western Railway. Project folder, Oct 2026.  
    <span class="use">Used for: First application of the model (see the swr-service-recovery-flows repository).</span>

### Software

28. *Python: NumPy, pandas, SciPy, GeoPandas, Shapely, pyogrio, pyarrow, Numba, statsmodels, Matplotlib*. Open-source projects. Python packages.  
    <span class="use">Used for: Modelling, assignment, statistics and figures.</span>
29. *pandoc, Beautiful Soup, lxml*. Open-source projects. Document tools.  
    <span class="use">Used for: Confluence storage format, Word and Markdown versions of the documents.</span>
