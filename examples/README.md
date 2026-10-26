# Examples: using railflow in other projects

Each example reads a railflow run through `railflow.api.RailFlow` and writes to its own `outputs/` folder.
They are described in `docs/applications.html`.

| Example | Project | What the model adds |
|---|---|---|
| `split_ticketing/split_ticket_demand.py` | Split Ticket Calculator (GWR fares) | Journeys through candidate split stations, demand on each flow, revenue-at-risk ranking of STOs |
| `flow_classification/flow_features.py` | Flow Classification (Integrated Fares Model) | Route distance and modelled journeys for every flow; demand-weighted cluster summaries |
| `performance_weighting/passenger_weights.py` | T3 & Cancellation Prediction | Passenger-km weights by region and line for passenger-weighted performance and model weighting |

```
python -m railflow run --data data --out outputs        # once
python examples/split_ticketing/split_ticket_demand.py   # uses ./outputs by default (or --out DIR)
```
