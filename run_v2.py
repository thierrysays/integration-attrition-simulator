"""Version 2 : recalage sur 3 départs hors personnes clés sur trois ans, comparaison
équipe majoritairement freelance et équipe salariée, courbe de basculement.

Usage : python3 run_v2.py
Produit : resultats_v2_scenarios.csv, resultats_v2_courbe.csv, distance_seuil_v2.png
"""
from __future__ import annotations

import csv
import statistics as st
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pmi_model_v2 import IntegrationModel, Params

OUT = Path(__file__).parent
BASE = Params()
Q0, G0 = 0.002, 0.012

LEVERS = {
    "base": {},
    "sans_prime": dict(retention_bonus=False),
    "sans_budget": dict(rolling_budget=False),
    "sans_parallele": dict(parallel_run=False),
    "sans_aucun_levier": dict(retention_bonus=False, rolling_budget=False, parallel_run=False),
}


def run_many(p, n=40, seed0=1000):
    return [IntegrationModel(p, seed=seed0 + i).run() for i in range(n)]


def scaled(p, s):
    return replace(p, base_quit=Q0 * s, quit_gain=G0 * s)


def calibrate(p, target=3.0, lo=0.005, hi=1.0, iters=14, n=50):
    for _ in range(iters):
        mid = (lo + hi) / 2
        mean = st.mean(m.departures_other for m in run_many(scaled(p, mid), n=n, seed0=5000))
        lo, hi = (mid, hi) if mean < target else (lo, mid)
    return (lo + hi) / 2


def agg(models):
    rows = [m.summary() for m in models]
    out = {"spiral_rate": sum(r["spiral"] for r in rows) / len(rows)}
    for k in ("min_headcount", "progress", "final_debt", "revenue_lost",
              "departures_key", "departures_other", "rework_share"):
        out[k] = st.mean(r[k] for r in rows)
    return out


def main():
    # Équipe distribuée : 10 % d'effort perdu en coordination, montée en compétence
    # de 24 semaines au lieu de 16, contagion des départs réduite de moitié.
    structures = {
        "freelance_distribue": replace(BASE, freelance_share=0.65, coordination_penalty=0.10,
                                       onboarding_weeks=24, w_dep=1.5),
        "freelance_regroupe": replace(BASE, freelance_share=0.65),
        "salaries_regroupes": replace(BASE, freelance_share=0.0),
    }
    factors, rows = {}, []
    for label, p in structures.items():
        s = calibrate(p)
        factors[label] = s
        print(f"\n=== {label} : facteur de calibration {s:.4f}")
        print(f"{'scénario':20s} spirale  eff.min  avanc.  dette  rev.perdu  dép.clés  dép.autres  reprise")
        for name, kw in LEVERS.items():
            r = agg(run_many(replace(scaled(p, s), **kw)))
            rows.append([label, name] + [round(v, 4) for v in r.values()])
            print(f"{name:20s} {r['spiral_rate']:6.0%}  {r['min_headcount']:7.2f}  {r['progress']:6.2f}  "
                  f"{r['final_debt']:5.2f}  {r['revenue_lost']:8.1%}  {r['departures_key']:8.1f}  "
                  f"{r['departures_other']:10.1f}  {r['rework_share']:6.1%}")
    with open(OUT / "resultats_v2_scenarios.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["structure", "scenario", "spirale", "eff_min", "avancement", "dette", "revenu_perdu",
                    "departs_cles", "departs_autres", "reprise"])
        w.writerows(rows)

    mults = [1, 2, 3, 4, 6, 8, 12, 16]
    curve = {}
    print("\n=== Courbe de basculement (multiples de l'attrition calibrée)")
    print(f"{'x':>4s}  " + "  ".join(f"{lab}/{cas:>6s}" for lab in structures for cas in ("base", "nolev")))
    for m in mults:
        line = []
        for label, p in structures.items():
            pm = scaled(p, factors[label] * m)
            b = agg(run_many(pm, n=60))["spiral_rate"]
            n0 = agg(run_many(replace(pm, retention_bonus=False, rolling_budget=False, parallel_run=False), n=60))["spiral_rate"]
            curve.setdefault((label, "base"), []).append(b)
            curve.setdefault((label, "nolev"), []).append(n0)
            line += [b, n0]
        print(f"{m:4d}  " + "  ".join(f"{v:>14.0%}" for v in line))
    with open(OUT / "resultats_v2_courbe.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["multiple"] + [f"{a}_{b}" for (a, b) in curve])
        for i, m in enumerate(mults):
            w.writerow([m] + [round(curve[k][i], 3) for k in curve])

    fig, ax = plt.subplots(figsize=(8.3, 4.3))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#888780")
        ax.spines[s].set_linewidth(0.6)
    ax.grid(axis="y", color="#D3D1C7", linewidth=0.5)
    ax.tick_params(colors="#444441", labelsize=9)
    style = {("freelance_distribue", "base"): ("#0F6E56", "-", "Freelance distribué, trois leviers"),
             ("freelance_distribue", "nolev"): ("#A32D2D", "-", "Freelance distribué, sans levier"),
             ("freelance_regroupe", "base"): ("#0F6E56", "--", "Freelance regroupé, trois leviers"),
             ("freelance_regroupe", "nolev"): ("#A32D2D", "--", "Freelance regroupé, sans levier"),
             ("salaries_regroupes", "base"): ("#0F6E56", ":", "Salariés regroupés, trois leviers"),
             ("salaries_regroupes", "nolev"): ("#A32D2D", ":", "Salariés regroupés, sans levier")}
    for k, (color, ls, label) in style.items():
        ax.plot(mults, curve[k], color=color, linestyle=ls, linewidth=1.7, marker="o", markersize=3.5, label=label)
    ax.set_xscale("log", base=2)
    ax.set_xticks(mults)
    ax.set_xticklabels([f"x{m}" for m in mults])
    ax.set_ylim(-0.03, 1.05)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])
    ax.set_xlabel("Attrition hors personnes clés, en multiples du cas observé (3 départs sur 3 ans)", fontsize=9, color="#444441")
    ax.set_ylabel("Part des tirages en spirale", fontsize=9, color="#444441")
    ax.set_title("Distance au seuil de basculement, selon la structure de l'équipe", fontsize=10, loc="left", color="#2C2C2A")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    fig.text(0.01, 0.01, "Paramètres synthétiques, équipe de 40, recalage à 3 départs dans chaque structure. 60 tirages par point.",
             fontsize=8, color="#5F5E5A")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "distance_seuil_v2.png", dpi=160, facecolor="white")
    print("\nFigure : distance_seuil_v2.png")


if __name__ == "__main__":
    main()
