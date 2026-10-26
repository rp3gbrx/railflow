"""Command line interface.

    python -m railflow run  [--data DIR] [--out DIR] [--steps all|tripends,network,...] [--recalibrate]
    python -m railflow info [--out DIR]

Steps, in order: tripends, network, zones, distribution, validation, assignment, exports, figures.
"""
import argparse
import importlib
import json
import os
import platform
import time
from datetime import datetime, timezone

STEPS = ["tripends", "network", "zones", "distribution", "validation", "assignment", "exports", "figures"]


def run(args):
    os.environ["RAILFLOW_DATA_DIR"] = args.data
    os.environ["RAILFLOW_OUTPUT_DIR"] = args.out
    if args.recalibrate:
        os.environ["RECALIBRATE"] = "1"
    from . import config as C
    steps = STEPS if args.steps == "all" else [s.strip() for s in args.steps.split(",")]
    meta_p = C.WORK / "metadata.json"
    for s in steps:
        if s not in STEPS:
            raise SystemExit(f"Unknown step {s}; choose from {STEPS}")
    for s in steps:
        t0 = time.time()
        print(f"\n=== {s} ===", flush=True)
        importlib.import_module(f"railflow.{s}").main()
        # metadata is updated after every step, so a failed run still records what completed
        meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
        meta.update({"model": C.MODEL_NAME, "version": C.MODEL_VERSION, "base_year": C.BASE_YEAR,
                     "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "python": platform.python_version(),
                     "data_dir": str(C.DATA), "steps_seconds": {**meta.get("steps_seconds", {}), s: round(time.time() - t0, 1)},
                     "assumptions": {"season_divisor": C.SEASON_DIVISOR, "ordinary_divisor": C.ORDINARY_DIVISOR,
                                     "unnamed_way_penalty": C.UNNAMED_WAY_PENALTY, "min_dist_km": C.MIN_DIST_KM}})
        meta_p.write_text(json.dumps(meta, indent=1))
    print(f"\nDone. Model files in {C.WORK}")


def info(args):
    from .api import RailFlow
    rf = RailFlow(args.out)
    print(json.dumps(rf.metadata, indent=1))
    st = rf.stations
    print(f"{len(st)} stations; weekday journeys {rf.matrix('B', 'awd').sum()/1e6:.2f}m; annual {rf.matrix('B', 'ann').sum()/1e6:.0f}m")


def main():
    ap = argparse.ArgumentParser(prog="railflow", description="GB rail trip distribution and network flow model")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="build the model")
    r.add_argument("--data", default="data"); r.add_argument("--out", default="outputs")
    r.add_argument("--steps", default="all"); r.add_argument("--recalibrate", action="store_true",
                                                          help="re-fit the deterrence functions even if outputs/model/theta.npy exists")
    r.set_defaults(func=run)
    i = sub.add_parser("info", help="summarise a model run"); i.add_argument("--out", default="outputs"); i.set_defaults(func=info)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
