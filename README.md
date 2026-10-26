# railflow

GB rail trip distribution and network flow model. railflow estimates journeys between every pair of
stations in Great Britain (annual and average weekday) and loads them onto the rail network.

- **Trip ends** from ORR station usage (Table 1410), converted to an average weekday by ticket type.
- **Model A:** doubly constrained gravity model with 22 region-level log-normal deterrence functions
  (11 ITL1 regions × internal/external), calibrated jointly to ORR Table 1595 trip-length distributions,
  following the ETC 2018 RailWatch Train Occupancy Model.
- **Model B:** Model A fused with every observed count ORR publishes (2,540 station main flows fixed,
  19,288 local-authority pair totals imposed). The default for network loading.
- **Assignment** all-or-nothing to an OpenStreetMap rail network, with station throughput and screenlines.

Version 0.1.0, base year 2024-25: 2,586 stations, 1,532m journeys a year, 4.78m on an average weekday.

## Documents

| Document | HTML (GitHub / browser) | Confluence pack |
|---|---|---|
| Technical document: development, method, validation, interface, improvement roadmap | `docs/technical_document.html` | `docs/confluence/technical_document/` |
| Applications: worked examples for the Split Ticket Calculator, Flow Classification and T3 & Cancellation projects | `docs/applications.html` | `docs/confluence/applications/` |
| Sources | `docs/sources.html` | `docs/confluence/sources/` |

Markdown versions (`docs/*.md`) render directly on GitHub. Uploading to Confluence: see `docs/README_CONFLUENCE.md`.

## Quick start

```bash
pip install -e .                                   # Python 3.11+
# put the input files in data/ (see data/README.md)
python -m railflow run --data data --out outputs    # about 4 minutes; reuses stored parameters if present
python -m railflow info --out outputs
```

Steps can be run individually: `--steps tripends,network,zones,distribution,validation,assignment,exports,figures`.
`--recalibrate` re-fits the deterrence functions (about 5 minutes).

## Using the model from another project

```python
from railflow.api import RailFlow
rf = RailFlow("path/to/railflow/outputs")
T = rf.matrix("B", "awd")            # station x station trips, average weekday
rf.od("B", "awd")                    # long table of station pairs
rf.passing_through("PEW")            # OD pairs routed through a station
rf.route_stations("WEY", "MKM")      # stations on the modelled route
rf.screenline("VXH", "WAT")          # two-way corridor flow between two stations
rf.assign(T_segment)                 # edge flows for any S x S matrix
rf.metadata["version"]               # record with your results
```

Projects keep their own code in their own repositories and point at a model run, for example with an
environment variable (the SWR Service Recovery project uses `SWR_RAILFLOW_OUTPUT`). Examples are in `examples/`.

## Repository layout

```
railflow/            the model package
  config.py          every assumption not read from data (weekday factors, penalties, regions)
  tripends.py  network.py  zones.py  distribution.py  validation.py  assignment.py  exports.py  figures.py
  api.py             read-only interface for other projects
  cli.py             python -m railflow run | info
tests/               core numerical tests (pytest)
data/                inputs (README.md lists sources, licences and checksums)
examples/            split_ticketing/  flow_classification/  performance_weighting/
docs/                templates/, build_docs.py, style.css, sources.py, generated HTML, Markdown and Confluence packs
tools/               html2confluence.py, publish_to_confluence.py, reference.docx
outputs/             written by a run (not committed)
```

## Rebuilding the documents

```bash
python examples/split_ticketing/split_ticket_demand.py
python examples/flow_classification/flow_features.py
python examples/performance_weighting/passenger_weights.py
python docs/build_docs.py            # needs beautifulsoup4, lxml and pandoc for the Confluence/Word/Markdown versions
```

All numbers in the documents are read from the run, so they always match it.

## Development

```bash
pip install -e .[dev] && pytest        # core numerical tests
```


Improvements are planned in the roadmap section of the technical document (observed ODM, LENNON
segmentation, timetable-based costs, train-level assignment, freight, Network Rail network).
Each is intended as a separate minor release; record changes in the change log of
`docs/templates/technical_document.html` and bump `MODEL_VERSION` in `railflow/config.py`,
`__version__` in `railflow/__init__.py` and `version` in `pyproject.toml`.

## Licence and attribution

Contains ORR data licensed under the Open Government Licence v3.0 and OpenStreetMap data
© OpenStreetMap contributors, available under the Open Database Licence.
