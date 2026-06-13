#!/usr/bin/env python3
"""Reconcile retort's omp-reported OpenRouter cost against OpenRouter's billing API.

omp's self-reported per-call cost was observed ~8% low on cache-heavy calls (see
experiment-15/PILOT.md, Step 0), so the billing API is the dataset of record. This
script cross-checks three independent sources:

  /generation?id=   per-run authoritative billed cost   (inference key)
  /credits          account aggregate total_usage        (inference key)
  /activity         per-model/day usage breakdown        (MANAGEMENT key)

For each run it reads the generation ids retort persisted (run_results._cost_usd
row, metadata_json -> openrouter_generation_ids), sums /generation over them to get
the billed per-run cost, and flags any run or model whose omp-reported cost diverges
from billed by more than --threshold.

Keys resolve from env (OPENROUTER_API_KEY / OPENROUTER_MGMT_KEY) else 1Password (op).
Usage:
  python validate_openrouter_spend.py --db experiment-15/retort.db
  python validate_openrouter_spend.py --db experiment-15/retort.db --json
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date
from urllib.parse import urlencode

API = "https://openrouter.ai/api/v1"
INFERENCE_REF = "op://Private/OpenRouter - Initial Retort Key/credential"
MGMT_REF = "op://Private/OpenRouter Management Key - Retort Experiments/credential"


# --------------------------------------------------------------------------- #
# Key resolution + HTTP
# --------------------------------------------------------------------------- #
def op_read(ref: str) -> str | None:
    try:
        out = subprocess.run(
            ["op", "read", ref], capture_output=True, text=True, timeout=30
        )
        return (out.stdout or "").strip() or None
    except Exception:
        return None


def resolve_key(env_name: str, op_ref: str) -> str | None:
    return os.environ.get(env_name) or op_read(op_ref)


def http_get(path: str, key: str, params: dict | None = None) -> dict | None:
    url = f"{API}{path}" + (f"?{urlencode(params)}" if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:      # rate limited — back off
                time.sleep(2 * (attempt + 1))
                continue
            if e.code in (404,):                    # gen not yet billed / unknown id
                return None
            raise
        except urllib.error.URLError:
            if attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    return None


def get_generation(gid: str, key: str) -> dict | None:
    # /generation can lag a few seconds behind the call; retry a couple times.
    for attempt in range(3):
        d = http_get("/generation", key, {"id": gid})
        if d:
            return d.get("data", d)
        time.sleep(1.5 * (attempt + 1))
    return None


def get_credits(key: str) -> dict:
    return (http_get("/credits", key) or {}).get("data", {})


def get_activity(mgmt_key: str) -> list[dict]:
    d = http_get("/activity", mgmt_key)
    return (d or {}).get("data", []) or []


# --------------------------------------------------------------------------- #
# DB
# --------------------------------------------------------------------------- #
def read_runs(db_path: str) -> list[dict]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    runs = []
    rows = con.execute(
        "SELECT id, run_config_json, status FROM experiment_runs ORDER BY id"
    ).fetchall()
    for r in rows:
        cfg = json.loads(r["run_config_json"] or "{}")
        cost_row = con.execute(
            "SELECT value, metadata_json FROM run_results "
            "WHERE run_id=? AND metric_name='_cost_usd'",
            (r["id"],),
        ).fetchone()
        meta = {}
        omp_cost = None
        if cost_row:
            omp_cost = cost_row["value"]
            if cost_row["metadata_json"]:
                meta = json.loads(cost_row["metadata_json"])
        ids_csv = meta.get("openrouter_generation_ids", "")
        gen_ids = [g for g in ids_csv.split(",") if g]
        sum_turns = meta.get("omp_cost_sum_all_turns")
        runs.append(
            {
                "run_id": r["id"],
                "status": r["status"],
                "model": cfg.get("model"),
                "omp_cost": omp_cost,
                "omp_cost_sum_all_turns": float(sum_turns) if sum_turns else None,
                "gen_ids": gen_ids,
                "upstream": meta.get("upstream_provider"),
            }
        )
    con.close()
    return runs


def activity_model(run_model: str) -> str:
    """run model 'openrouter/<provider>/<id>' -> activity slug '<provider>/<id>'."""
    prefix = "openrouter/"
    return run_model[len(prefix):] if run_model.startswith(prefix) else run_model


# --------------------------------------------------------------------------- #
# Reconcile
# --------------------------------------------------------------------------- #
def pct(a: float, b: float) -> float:
    return 100.0 * (a - b) / b if b else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True, help="Path to the experiment retort.db")
    ap.add_argument("--date", default=str(date.today()),
                    help="YYYY-MM-DD to filter /activity rows (default: today)")
    ap.add_argument("--threshold", type=float, default=5.0,
                    help="Flag |omp-billed| gaps exceeding this percent (default 5)")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    args = ap.parse_args()

    inf_key = resolve_key("OPENROUTER_API_KEY", INFERENCE_REF)
    mgmt_key = resolve_key("OPENROUTER_MGMT_KEY", MGMT_REF)
    if not inf_key:
        print("ERROR: no inference key (OPENROUTER_API_KEY / op).", file=sys.stderr)
        return 2

    runs = read_runs(args.db)

    # Per-run reconcile via /generation.
    gen_cache: dict[str, float | None] = {}
    for run in runs:
        billed = 0.0
        missing = 0
        for gid in run["gen_ids"]:
            if gid not in gen_cache:
                g = get_generation(gid, inf_key)
                gen_cache[gid] = float(g.get("total_cost", 0.0)) if g else None
            c = gen_cache[gid]
            if c is None:
                missing += 1
            else:
                billed += c
        run["billed"] = billed if run["gen_ids"] else None
        run["missing_gen"] = missing

    # Per-model aggregation.
    per_model: dict[str, dict] = defaultdict(
        lambda: {"omp": 0.0, "billed": 0.0, "runs": 0, "ids": 0}
    )
    for run in runs:
        m = run["model"] or "?"
        per_model[m]["runs"] += 1
        per_model[m]["ids"] += len(run["gen_ids"])
        if run["omp_cost"]:
            per_model[m]["omp"] += run["omp_cost"]
        if run["billed"]:
            per_model[m]["billed"] += run["billed"]

    # /activity cross-check (management key), filtered to our models + date.
    activity_by_model: dict[str, float] = defaultdict(float)
    activity_available = bool(mgmt_key)
    if mgmt_key:
        wanted = {activity_model(m) for m in per_model}
        for row in get_activity(mgmt_key):
            if row.get("date", "").startswith(args.date) and row.get("model") in wanted:
                activity_by_model[row["model"]] += float(row.get("usage", 0.0))

    credits = get_credits(inf_key)

    if args.json:
        print(json.dumps(
            {"runs": runs, "per_model": per_model,
             "activity_by_model": activity_by_model, "credits": credits}, indent=2))
        return 0

    # ---- table report ----
    print(f"\nOpenRouter spend reconciliation — {args.db}")
    print(f"credits: total_usage=${credits.get('total_usage', '?')} "
          f"of {credits.get('total_credits', '?')}\n")

    print("PER RUN (billed = sum /generation over the run's generation ids)")
    print(f"  {'run':>3} {'model':40} {'st':4} {'ids':>3} "
          f"{'omp$':>9} {'sumturns$':>10} {'billed$':>9} {'Δ omp%':>7} up")
    for run in runs:
        m = (run["model"] or "?").replace("openrouter/", "")
        omp = run["omp_cost"]
        billed = run["billed"]
        d = f"{pct(omp, billed):+.1f}" if (omp and billed) else "—"
        over = omp and billed and abs(pct(omp, billed)) > args.threshold
        flag = " ⚠" if over else ""
        miss = f" !{run['missing_gen']}miss" if run["missing_gen"] else ""
        print(f"  {run['run_id']:>3} {m[:40]:40} {str(run['status'])[:4]:4} "
              f"{len(run['gen_ids']):>3} "
              f"{(omp or 0):>9.5f} {(run['omp_cost_sum_all_turns'] or 0):>10.5f} "
              f"{(billed or 0):>9.5f} {d:>7}{flag}{miss} {run['upstream'] or ''}")

    print("\nPER MODEL")
    hdr_act = "activity$" if activity_available else "activity(n/a)"
    print(f"  {'model':40} {'runs':>4} {'omp$':>9} {'billed$':>9} "
          f"{hdr_act:>11} {'Δ omp%':>7}")
    tot_omp = tot_billed = tot_act = 0.0
    for m, v in sorted(per_model.items()):
        act = activity_by_model.get(activity_model(m), 0.0)
        tot_omp += v["omp"]
        tot_billed += v["billed"]
        tot_act += act
        d = f"{pct(v['omp'], v['billed']):+.1f}" if v["billed"] else "—"
        over = v["billed"] and abs(pct(v["omp"], v["billed"])) > args.threshold
        flag = " ⚠" if over else ""
        actstr = f"{act:.5f}" if activity_available else "—"
        print(f"  {m.replace('openrouter/',''):40} {v['runs']:>4} "
              f"{v['omp']:>9.5f} {v['billed']:>9.5f} {actstr:>11} {d:>7}{flag}")
    print(f"  {'TOTAL':40} {'':>4} {tot_omp:>9.5f} {tot_billed:>9.5f} "
          f"{(f'{tot_act:.5f}' if activity_available else '—'):>11} "
          f"{(f'{pct(tot_omp, tot_billed):+.1f}' if tot_billed else '—'):>7}")

    if not activity_available:
        print("\n(/activity skipped — no management key; set OPENROUTER_MGMT_KEY or "
              "store it in 1Password to enable the per-model billing cross-check.)")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
