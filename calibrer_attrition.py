"""Recalage de l'attrition sur le cas observé et distance au seuil de basculement.

Observation retenue : attrition minimaliste, environ 3 équivalents temps plein.
Deux lectures sont testées, car l'énoncé ne précise pas l'horizon :
    A : 3 départs hors personnes clés sur les trois ans
    B : 3 départs hors personnes clés par an, soit 9 sur trois ans

On met à l'échelle ensemble la probabilité de départ de base et la réaction à
l'incertitude (rapport conservé), jusqu'à reproduire le nombre de départs cible
dans le scénario de base. Hypothèse structurelle : équipe synthétique de 40.

Usage : python3 calibrer_attrition.py
"""
from __future__ import annotations

import csv
import statistics as st
from dataclasses import replace
from pathlib import Path

from run_scenarios import REFERENCE, agg, run_many

OUT = Path(__file__).parent
BASE_QUIT0, GAIN0 = 0.002, 0.012


def scaled(params, s):
    return replace(params, base_quit=BASE_QUIT0 * s, quit_gain=GAIN0 * s)


def mean_other(params, n=60):
    return st.mean(m.departures_other for m in run_many(params, n=n, seed0=5000))


def calibrate(target, lo=0.005, hi=1.0, iters=18):
    for _ in range(iters):
        mid = (lo + hi) / 2
        if mean_other(scaled(REFERENCE, mid)) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


LEVERS = {
    "base": {},
    "sans_prime": dict(retention_bonus=False),
    "sans_budget": dict(rolling_budget=False),
    "sans_parallele": dict(parallel_run=False),
    "sans_aucun_levier": dict(retention_bonus=False, rolling_budget=False, parallel_run=False),
}


def main():
    rows = []
    calibrations = {}
    for label, target in (("A_3_sur_3_ans", 3.0), ("B_3_par_an", 9.0)):
        s = calibrate(target)
        calibrations[label] = s
        print(f"\n=== Calibration {label} : facteur {s:.4f} "
              f"(probabilité de base {BASE_QUIT0*s:.5f} par semaine, réaction {GAIN0*s:.5f})")
        print(f"{'scénario':20s} spirale  eff.min  avanc.  dette  rev.perdu  dép.clés  dép.autres")
        for name, kw in LEVERS.items():
            r = agg(run_many(replace(scaled(REFERENCE, s), **kw)))
            rows.append([label, name] + [round(v, 4) for v in r.values()])
            print(f"{name:20s} {r['spiral_rate']:6.0%}  {r['min_headcount_mean']:7.2f}  "
                  f"{r['progress_mean']:6.2f}  {r['final_debt_mean']:5.2f}  "
                  f"{r['revenue_lost_mean']:8.1%}  {r['departures_key_mean']:8.1f}  "
                  f"{r['departures_other_mean']:9.1f}")

    keys = list(agg(run_many(REFERENCE, n=2)).keys())
    with open(OUT / "resultats_recales.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["calibration", "scenario"] + keys)
        w.writerows(rows)

    print("\n=== Distance au seuil : multiplicateur de l'attrition calibrée (lecture A)")
    s = calibrations["A_3_sur_3_ans"]
    print(f"{'multiplicateur':>14s}  {'dép.hors clés (base)':>21s}  {'spirale base':>12s}  {'spirale sans levier':>20s}")
    sweep = []
    for m in (1, 2, 4, 8, 16, 24, 32, 48):
        p = scaled(REFERENCE, s * m)
        b = agg(run_many(p))
        n0 = agg(run_many(replace(p, retention_bonus=False, rolling_budget=False, parallel_run=False)))
        sweep.append([m, round(b["departures_other_mean"], 1), b["spiral_rate"], n0["spiral_rate"]])
        print(f"{m:14d}  {b['departures_other_mean']:21.1f}  {b['spiral_rate']:12.0%}  {n0['spiral_rate']:20.0%}")
    with open(OUT / "resultats_distance_seuil.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["multiplicateur", "departs_hors_cles_base", "spirale_base", "spirale_sans_levier"])
        w.writerows(sweep)


if __name__ == "__main__":
    main()
