"""Build the railflow documents from a model run.

    python docs/build_docs.py [--out outputs] [--no-confluence]

Fills docs/templates/*.html with numbers read from the run and the example
outputs, inlines docs/style.css, copies figures to docs/figures/, writes
docs/technical_document.html, docs/applications.html and docs/sources.html,
and converts each to Confluence format in docs/confluence/<name>/ with
tools/html2confluence.py. Numbers in the documents therefore always match the
run they were built from.

Run the model (python -m railflow run) and the three examples first.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DOCS = Path(__file__).resolve().parent
REPO = DOCS.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(DOCS))
import sources  # noqa: E402

LINK_MAP = {"technical_document.html": "railflow technical document", "applications.html": "Using railflow in other projects: worked examples",
            "sources.html": "railflow sources"}


def pct(x, d=0):
    return f"{100 * x:.{d}f}%"


def table(df, num_cols=(), caption=None):
    h = "".join(f'<th class="n">{c}</th>' if c in num_cols else f"<th>{c}</th>" for c in df.columns)
    rows = "".join("<tr>" + "".join(f'<td class="n">{v}</td>' if c in num_cols else f"<td>{html.escape(str(v))}</td>"
                                    for c, v in zip(df.columns, r)) + "</tr>" for r in df.itertuples(index=False))
    cap = f'<p class="meta">{caption}</p>' if caption else ""
    return f'{cap}<div class="tbl"><table><thead><tr>{h}</tr></thead><tbody>{rows}</tbody></table></div>'


def fill(name, vals, style):
    tpl = (DOCS / "templates" / f"{name}.html").read_text(encoding="utf-8")
    vals = {**vals, "style": style}
    missing = sorted(set(re.findall(r"\[\[(\w+)\]\]", tpl)) - set(vals))
    if missing:
        raise SystemExit(f"{name}: no value for placeholders {missing}")
    out = re.sub(r"\[\[(\w+)\]\]", lambda m: str(vals[m.group(1)]), tpl)
    (DOCS / f"{name}.html").write_text(out, encoding="utf-8")
    print(f"wrote docs/{name}.html")


def technical_values(out):
    from railflow.api import RailFlow
    rf = RailFlow(out)
    W, T = out / "model", out / "tables"
    st = rf.stations
    meta, cal = rf.metadata, json.loads((W / "calibration.json").read_text())
    v = json.loads((T / "validation_summary.json").read_text())
    par = pd.read_csv(T / "deterrence_parameters.csv")
    mo = pd.read_csv(T / "main_od_validation.csv")
    la = pd.read_csv(T / "la_assignment_check.csv")
    pg = pd.read_csv(T / "paper_table1_comparison.csv")
    sn = pd.read_csv(W / "station_nodes.csv")
    ef = rf.edges
    kinds = ef.groupby("kind").length_m.agg(["size", "sum"])
    sk, ix = rf.skim, rf.index
    sw = mo[((mo.crs_i == "SUR") & (mo.crs_j == "WAT")) | ((mo.crs_i == "WAT") & (mo.crs_j == "SUR"))].iloc[0]
    rail = ef[ef.kind != "tube"]
    pkm_A = (rail.flow_TA_ann * rail.length_m).sum() / 1e3; pkm_B = (rail.flow_TB_ann * rail.length_m).sum() / 1e3   # excl. London transfer links
    J = st.ee_all.sum() / 2
    orr_km = 64.6e9 / 1729e6
    os.environ.setdefault("RAILFLOW_OUTPUT_DIR", str(out))   # railflow.config creates its folders on import
    from railflow import config as C
    secs = meta.get("steps_seconds", {})
    names = {"tripends": "trip ends", "network": "network", "zones": "zones", "distribution": "distribution", "validation": "validation",
             "assignment": "assignment", "exports": "exports", "figures": "figures"}
    vals = {
        "date": dt.date.today().strftime("%-d %B %Y"), "version": meta.get("version", "?"), "base_year": meta.get("base_year", "?"),
        "n_stations": f"{len(st):,}", "annual_m": f"{J / 1e6:,.0f}", "awd_m": f"{st.ee_awd.sum() / 2 / 1e6:.2f}",
        "annualisation": f"{st.ee_all.sum() / st.ee_awd.sum():.0f}", "season_div": f"{C.SEASON_DIVISOR:g}", "ord_div": f"{C.ORDINARY_DIVISOR:.1f}",
        "track_km": f"{kinds.loc['osm', 'sum'] / 1e3:,.0f}", "n_osm": f"{int(kinds.loc['osm', 'size']):,}",
        "unnamed_pen": f"{C.UNNAMED_WAY_PENALTY:g}", "min_km": f"{C.MIN_DIST_KM:g}",
        "snap_far": f"{(sn.snap_m > 1000).sum()}",
        "d_wat_sou": f"{sk[ix['WAT'], ix['SOU']]:.1f}", "d_wat_exd": f"{sk[ix['WAT'], ix['EXD']]:.1f}", "d_wey_mkm": f"{sk[ix['WEY'], ix['MKM']]:.1f}",
        "la_misalloc": pct((la.ee_1410 - la.ee_1595).abs().sum() / la.ee_1595.sum() / 2, 1),
        "n_resid": f"{cal.get('n_residuals', 605)}", "cost0": f"{cal['initial_cost']:.1f}", "cost1": f"{cal['final_cost']:.2f}",
        "nev": f"{cal['evaluations']:,}", "cal_min": f"{cal['seconds'] / 60:.0f}",
        "n_fixed": f"{cal['fusion_fixed_cells']:,}", "fuse_it": f"{cal['fusion_iterations']}", "fuse_err": pct(cal["fusion_la_error"], 1),
        "fuse_te": pct(cal["fusion_trip_end_error"], 1),
        "sur_wat_A": f"{sw.modelA / 1e6:.2f} million", "sur_wat_obs": f"{sw.observed / 1e6:.2f} million",
        "main_od_share": pct(v["main_od_share_of_journeys"]),
        "int_share_mae": f"{(par.modelA_int_share - par.obs_int_share).abs().mean() * 100:.1f} pts",
        "la_pairs": f"{v['la_pairs']:,}", "r2A": f"{v['r2_lin_A']:.2f} / {v['r2_log_A']:.2f}", "r2B": f"{v['r2_lin_B']:.3f}",
        "la100_err": f"{v['median_abs_pct_err_A_100k']:.0f}%", "la100_n": f"{v['la_pairs_100k']:,}",
        "ho_n": f"{v['holdout_pairs']:,}", "ho_A": pct(v["holdout_modelA_within_25pct"]), "ho_B": pct(v["holdout_modelB_80pct_within_25pct"]),
        "ho_A_ratio": f"{v['holdout_modelA_median_ratio']:.2f}", "ho_B_ratio": f"{v['holdout_modelB_80pct_median_ratio']:.2f}",
        "ho_LA": pct(v["holdout_modelB_LAonly_within_25pct"]), "ho_LA_ratio": f"{v['holdout_modelB_LAonly_median_ratio']:.2f}",
        "mean_km_A": f"{pkm_A / J:.1f} km", "mean_km_B": f"{pkm_B / J:.1f} km", "orr_mean_km": f"{orr_km:.1f} km",
        "longer_pct": pct(pkm_B / J / orr_km - 1), "pkm_A": f"{pkm_A / 1e9:.1f} bn", "pkm_B": f"{pkm_B / 1e9:.1f} bn",
        "runtime_min": f"{max(1, round(sum(secs.values()) / 60))}" if secs else "5",
        "runtimes": "; ".join(f"{names[k]} {secs[k]:.0f} s" for k in names if k in secs) or "not recorded",
    }
    for k, key in [("snap", "snap"), ("bridge", "bridge"), ("gap", "gap"), ("tube", "tube")]:
        vals[f"n_{k}"] = f"{int(kinds.loc[key, 'size']):,}"; vals[f"km_{k}"] = f"{kinds.loc[key, 'sum'] / 1e3:,.0f}"

    p = par.copy()
    p["Region"] = p.region
    g = lambda c: f'<span style="text-transform:none">{c}</span>'   # keep Greek letters lower case in upper-case headers
    greek = [("mu_int", g("μ") + " int"), ("sigma_int", g("σ") + " int"), ("mu_ext", g("μ") + " ext"), ("sigma_ext", g("σ") + " ext"), ("gamma_ext", g("γ") + " ext")]
    for a, b in greek:
        p[b] = p[a].map(lambda x: f"{x:.2f}")
    p["Internal share obs / model"] = [f"{a:.0%} / {b:.0%}" for a, b in zip(p.obs_int_share, p.modelA_int_share)]
    p["Mean km int obs / model"] = [f"{a:.0f} / {b:.0f}" for a, b in zip(p.obs_mean_km_int, p.modelA_mean_km_int)]
    p["Mean km ext obs / model"] = [f"{a:.0f} / {b:.0f}" for a, b in zip(p.obs_mean_km_ext, p.modelA_mean_km_ext)]
    cols = ["Region"] + [b for _, b in greek] + ["Internal share obs / model", "Mean km int obs / model", "Mean km ext obs / model"]
    vals["param_table"] = table(p[cols], num_cols=cols[1:], caption="Calibrated parameters (μ and σ on log-km) and fit to the observed regional distributions. Distances are between local-authority pairs.")

    q = pg[pg.model == "B"].copy()
    q["Group"] = q.group
    q["Internal, railflow"] = q.mean_km_int.map(lambda x: f"{x:.0f}"); q["Internal, paper"] = q.paper_AM_2018_int_km
    q["External, railflow"] = q.mean_km_ext.map(lambda x: f"{x:.0f}"); q["External, paper"] = q.paper_AM_2018_ext_km
    cols = ["Group", "Internal, railflow", "Internal, paper", "External, railflow", "External, paper"]
    vals["paper_table"] = ("<h3>Comparison with the RailWatch paper's Table 1</h3><p>Mean station-to-station trip lengths for the paper's seven regional groups (Model B). "
                           "The paper's figures are AM-peak trips from mobile network data in 2018, and its distributions stop at about 200 km, so they are context rather than a target. "
                           "The broad ordering is the same: London has the shortest internal trips, and Scotland, Yorkshire &amp; North, Wales and the Midlands have the longest external trips. "
                           "Internal means are shorter here because all-day travel includes many short off-peak trips, and external means are longer for distant regions because long trips are not truncated.</p>"
                           + table(q[cols], num_cols=cols[1:], caption="Mean trip length (km): railflow Model B, all day 2024-25; paper, AM peak 2018."))

    lt = pd.read_csv(T / "lines_max_flow.csv")
    lt = lt[lt.km >= 50].head(10)
    lt = pd.DataFrame({"Named line (OSM)": lt.name, "Track km": lt.km.map(lambda x: f"{x:,.0f}"),
                       "Peak section, Model B": lt.max_flow_B.map(lambda x: f"{x:,.0f}"), "Peak section, Model A": lt.max_flow_A.map(lambda x: f"{x:,.0f}")})
    vals["lines_table"] = table(lt, num_cols=list(lt.columns[1:]), caption="Busiest named lines (at least 50 km of track): highest two-way weekday flow on any section of the line.")
    vals["sources_section"] = sources.html_list()
    return vals


def application_values(out):
    from railflow.api import RailFlow
    rf = RailFlow(out)
    E = REPO / "examples"
    ex = pd.read_csv(E / "split_ticketing/outputs/stc_examples_demand.csv")
    th = pd.read_csv(E / "split_ticketing/outputs/split_station_through_journeys.csv")
    cl = pd.read_csv(E / "flow_classification/outputs/cluster_summary.csv", index_col=0)
    ff = pd.read_csv(E / "flow_classification/outputs/flow_features_ga_lo.csv.gz", usecols=["annual_journeys"])
    reg = pd.read_csv(E / "performance_weighting/outputs/weights_by_region.csv", index_col=0)
    lines = pd.read_csv(E / "performance_weighting/outputs/weights_by_line_top40.csv", index_col=0).head(10)
    wm = ex.iloc[0]
    meta = rf.metadata
    vals = {"date": dt.date.today().strftime("%-d %B %Y"), "version": meta.get("version", "?"), "base_year": meta.get("base_year", "?"),
            "wey_mkm": f"{wm.annual_journeys_modelB:,.0f}", "wey_mkm_rev": f"{wm.upper_bound_revenue_at_risk_gbp / 1e3:,.0f}",
            "wey_mkm_km": f"{wm.modelled_route_km:.1f}"}
    e = pd.DataFrame({"STC example": ex.flow.str.replace(", best split via ", " via ").str.replace(" to ", "–"), "Saving per journey": ex.saving_per_journey_gbp.map(lambda x: f"£{x:,.2f}"),
                      "Journeys a year (Model B)": ex.annual_journeys_modelB.map(lambda x: f"{x:,.1f}" if x < 10 else f"{x:,.0f}"),
                      "Upper-bound revenue at risk": ex.upper_bound_revenue_at_risk_gbp.map(lambda x: f"£{x:,.0f}" if x >= 1 else f"£{x:.2f}"),
                      "Split station on modelled route": ex.split_station_on_modelled_route.map({True: "Yes", False: "No"}),
                      "Route km": ex.modelled_route_km.map(lambda x: f"{x:.1f}")})
    vals["stc_examples_table"] = table(e, num_cols=list(e.columns[1:2]) + list(e.columns[2:4]) + ["Route km"],
                                       caption="The STC's worked examples with modelled demand (both directions).")
    t = th.copy()
    t = pd.DataFrame({"Station": t.station, "CRS": t.crs, "OD pairs routed through": t.od_pairs_through.map(lambda x: f"{x:,.0f}"),
                      "Through journeys a year": t.annual_journeys_through.map(lambda x: f"{x / 1e6:.2f}m"),
                      "Through journeys a weekday": t.weekday_journeys_through.map(lambda x: f"{x:,.0f}"),
                      "Entries + exits a year": t.station_entries_exits_annual.map(lambda x: f"{x / 1e6:.2f}m")})
    vals["split_station_table"] = table(t, num_cols=list(t.columns[2:]), caption="Candidate split stations, ranked by journeys passing through.")
    pew = th.set_index("crs").loc["PEW"]
    vals["pew_through"] = f"{pew.annual_journeys_through / 1e6:.1f}"; vals["pew_ee"] = f"{pew.station_entries_exits_annual / 1e3:,.0f}"

    cl["share_of_flows"] = cl.flows / cl.flows.sum(); cl["share_of_journeys"] = cl.journeys / cl.journeys.sum()   # unrounded
    c0 = cl.share_of_journeys.idxmax()
    vals["c0_flows"] = pct(cl.loc[c0, "share_of_flows"]); vals["c0_journeys"] = pct(cl.loc[c0, "share_of_journeys"])
    longc = cl[cl.crowfly_km_median > 100]
    vals["long_flows"] = pct(longc.share_of_flows.sum()); vals["long_journeys"] = pct(longc.share_of_journeys.sum(), 1)
    vals["n_flows"] = f"{len(ff):,}"; vals["flows_journeys"] = f"{ff.annual_journeys.sum() / 1e6:,.0f}"
    c = pd.DataFrame({"Cluster": cl.index, "Flows": cl.flows.map(lambda x: f"{x:,}"), "Share of flows": cl.share_of_flows.map(pct),
                      "Share of journeys": cl.share_of_journeys.map(pct), "Median crow-fly km": cl.crowfly_km_median.map(lambda x: f"{x:.0f}"),
                      "Median network km": cl.network_km_median.map(lambda x: f"{x:.0f}"),
                      "Median journeys per flow": cl.journeys_per_flow_median.map(lambda x: f"{x:,.0f}"),
                      "Median commute share": cl.commute_share.map(pct)})
    vals["cluster_table"] = table(c, num_cols=list(c.columns[1:]), caption="Cluster summary, ordered by median distance.")

    def rshare(r, col):
        return pct(reg.loc[r, col])
    vals.update({"lon_pkm": rshare("London", "pkm_share"), "lon_track": rshare("London", "track_km_share"),
                 "sco_pkm": rshare("Scotland", "pkm_share"), "sco_track": rshare("Scotland", "track_km_share")})
    r = pd.DataFrame({"Region": reg.index, "Passenger-km a year": reg.pkm_ann.map(lambda x: f"{x / 1e9:.1f} bn"),
                      "Share of passenger-km": reg.pkm_share.map(lambda x: pct(x, 1)), "Share of track-km": reg.track_km_share.map(lambda x: pct(x, 1)),
                      "Weekday passengers per track-km": reg.pax_per_track_km_awd.map(lambda x: f"{x:,.0f}")})
    vals["region_table"] = table(r, num_cols=list(r.columns[1:]), caption="Passenger weights by region (Model B, 2024-25).")
    lt = pd.DataFrame({"Named line (OSM)": lines.index, "Passenger-km a year": lines.pkm_ann.map(lambda x: f"{x / 1e9:.2f} bn"),
                       "Share of GB passenger-km": lines.pkm_share.map(lambda x: pct(x, 1)),
                       "Busiest section, weekday": lines.peak_section_flow_awd.map(lambda x: f"{x:,.0f}")})
    vals["lines_table"] = table(lt, num_cols=list(lt.columns[1:]), caption="Ten named lines with the most passenger-km. The file has the top 40.")
    return vals


def sources_page(style):
    body = sources.html_list()
    page = f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>railflow Sources</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Barlow:ital,wght@0,400;0,500;0,600;1,400&display=swap">
<style>
{style}
</style>
</head>
<body>
<main>
<p class="eyebrow">railflow · Sources</p>
<h1>railflow sources</h1>
<p class="meta">Every source used to build, document and apply the model. Generated from <code>docs/sources.py</code> on {dt.date.today().strftime("%-d %B %Y")}.</p>
<p>Documents supplied with the project have no public link and are shown in italics. All other entries link to the source.</p>
{body}
</main>
</body>
</html>
"""
    (DOCS / "sources.html").write_text(page, encoding="utf-8")
    print("wrote docs/sources.html")


def copy_figures(out):
    fig = DOCS / "figures"
    fig.mkdir(exist_ok=True)
    srcs = list((out / "figures").glob("*.png")) + list((REPO / "examples").glob("*/outputs/*.png"))
    for p in srcs:
        shutil.copy(p, fig / p.name)
    print(f"copied {len(srcs)} figures to docs/figures/")


def confluence(names):
    for n in names:
        subprocess.run([sys.executable, str(REPO / "tools" / "html2confluence.py"), str(DOCS / f"{n}.html"),
                        "--out", str(DOCS / "confluence" / n), "--link-map", json.dumps(LINK_MAP)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(REPO / "outputs")); ap.add_argument("--no-confluence", action="store_true")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    style = (DOCS / "style.css").read_text(encoding="utf-8")
    copy_figures(out)
    fill("technical_document", technical_values(out), style)
    fill("applications", application_values(out), style)
    sources_page(style)
    if not a.no_confluence:
        confluence(["technical_document", "applications", "sources"])


if __name__ == "__main__":
    main()
