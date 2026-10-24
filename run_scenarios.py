"""Scénarios de désactivation des leviers et balayage de sensibilité.

Usage : python3 run_scenarios.py
Produit : resultats_scenarios.csv, resultats_sensibilite.csv, scenarios.png
"""
from __future__ import annotations

import csv
import statistics as st
from dataclasses import replace
from pathlib import Path

from pmi_model import IntegrationModel, Params

N_RUNS = 40
OUT = Path(__file__).parent

REFERENCE = Params(debt0=0.80)
LOW_DEBT = Params(debt0=0.30)  # niveau de dette plus faible, même structure

SCENARIOS = {
    "reference_base": REFERENCE,
    "reference_sans_prime": replace(REFERENCE, retention_bonus=False),
    "reference_sans_budget": replace(REFERENCE, rolling_budget=False),
    "reference_sans_parallele": replace(REFERENCE, parallel_run=False),
    "reference_sans_prime_ni_budget": replace(REFERENCE, retention_bonus=False, rolling_budget=False),
    "reference_sans_aucun_levier": replace(
        REFERENCE, retention_bonus=False, rolling_budget=False, parallel_run=False
    ),
    # Contrôles : boucles de rétroaction coupées (l'incertitude ne dépend plus du
    # retard, du revenu ni des départs). L'écart avec les scénarios correspondants
    # mesure la part de l'effondrement due aux boucles, et non à l'attrition ordinaire.
    "controle_sans_budget_boucles_coupees": replace(
        REFERENCE, rolling_budget=False, w_slip=0.0, w_rev=0.0, w_dep=0.0
    ),
    "controle_sans_aucun_levier_boucles_coupees": replace(
        REFERENCE, retention_bonus=False, rolling_budget=False, parallel_run=False,
        w_slip=0.0, w_rev=0.0, w_dep=0.0,
    ),
    "dette_faible_base": LOW_DEBT,
    "dette_faible_sans_aucun_levier": replace(
        LOW_DEBT, retention_bonus=False, rolling_budget=False, parallel_run=False
    ),
}


def run_many(params: Params, n: int = N_RUNS, seed0: int = 1000):
    return [IntegrationModel(params, seed=seed0 + i).run() for i in range(n)]


def agg(models):
    rows = [m.summary() for m in models]
    out = {"spiral_rate": sum(r["spiral"] for r in rows) / len(rows)}
    for k in (
        "min_headcount", "final_headcount", "progress", "final_slippage",
        "final_debt", "revenue_lost", "departures_key", "departures_other",
    ):
        vals = [r[k] for r in rows]
        out[k + "_mean"] = st.mean(vals)
        out[k + "_sd"] = st.pstdev(vals)
    return out


def main() -> None:
    results, runs = {}, {}
    for name, params in SCENARIOS.items():
        models = run_many(params)
        runs[name] = models
        results[name] = agg(models)

    cols = ["scenario"] + list(next(iter(results.values())).keys())
    with open(OUT / "resultats_scenarios.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for name, r in results.items():
            w.writerow([name] + [round(v, 4) for v in r.values()])

    print(f"{'scénario':34s} spirale  eff.min  avanc.  dette  rev.perdu  dép.clés  dép.autres")
    for name, r in results.items():
        print(
            f"{name:34s} {r['spiral_rate']:6.0%}  {r['min_headcount_mean']:7.2f}  "
            f"{r['progress_mean']:6.2f}  {r['final_debt_mean']:5.2f}  "
            f"{r['revenue_lost_mean']:8.1%}  {r['departures_key_mean']:8.1f}  "
            f"{r['departures_other_mean']:9.1f}"
        )

    sweep_rows = []
    gains = [0.006, 0.012, 0.018, 0.024, 0.036, 0.048]
    print("\nSensibilité : taux de spirale selon l'intensité de la réaction à l'incertitude")
    print(f"{'quit_gain':>10s}  {'base':>6s}  {'sans prime+budget':>18s}  {'sans aucun levier':>18s}")
    for g in gains:
        base = agg(run_many(replace(REFERENCE, quit_gain=g)))
        mid = agg(run_many(replace(REFERENCE, quit_gain=g, retention_bonus=False, rolling_budget=False)))
        none = agg(
            run_many(
                replace(REFERENCE, quit_gain=g, retention_bonus=False, rolling_budget=False, parallel_run=False)
            )
        )
        sweep_rows.append([g, base["spiral_rate"], mid["spiral_rate"], none["spiral_rate"]])
        print(f"{g:10.3f}  {base['spiral_rate']:6.0%}  {mid['spiral_rate']:18.0%}  {none['spiral_rate']:18.0%}")
    with open(OUT / "resultats_sensibilite.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quit_gain", "spirale_base", "spirale_sans_prime_ni_budget", "spirale_sans_aucun_levier"])
        w.writerows([[r[0]] + [round(x, 3) for x in r[1:]] for r in sweep_rows])

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib absent : figure non produite")
        return

    show = {
        "reference_base": ("Base (trois leviers)", "#0F6E56"),
        "reference_sans_prime": ("Sans prime de rétention", "#534AB7"),
        "reference_sans_budget": ("Sans budget glissant", "#BA7517"),
        "reference_sans_aucun_levier": ("Sans aucun levier", "#A32D2D"),
    }
    weeks = range(1, REFERENCE.weeks + 1)
    fig, axes = plt.subplots(1, 2, figsize=(11.7, 4.2))
    for ax in axes:
        ax.set_facecolor("white")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color("#888780")
            ax.spines[s].set_linewidth(0.6)
        ax.tick_params(colors="#444441", labelsize=9)
        ax.grid(axis="y", color="#D3D1C7", linewidth=0.5)
    for name, (label, color) in show.items():
        ms = runs[name]
        for ax, key in ((axes[0], "headcount"), (axes[1], "progress")):
            series = list(zip(*[m.hist[key] for m in ms]))
            med = [st.median(x) for x in series]
            lo = [sorted(x)[int(0.1 * len(x))] for x in series]
            hi = [sorted(x)[int(0.9 * len(x)) - 1] for x in series]
            ax.plot(weeks, med, color=color, linewidth=1.6, label=label)
            ax.fill_between(weeks, lo, hi, color=color, alpha=0.10, linewidth=0)
    planned = runs["reference_base"][0].hist["planned"]
    axes[1].plot(weeks, planned, color="#444441", linewidth=0.9, linestyle="--", label="Plan")
    axes[0].axhline(0.6, color="#444441", linewidth=0.7, linestyle=":")
    axes[0].text(4, 0.61, "seuil de spirale (60 %)", fontsize=8, color="#444441")
    axes[0].set_title("Effectif d'ingénierie (part de l'effectif initial)", fontsize=10, loc="left", color="#2C2C2A")
    axes[1].set_title("Avancement de la migration (part du total)", fontsize=10, loc="left", color="#2C2C2A")
    for ax in axes:
        ax.set_xlabel("Semaines", fontsize=9, color="#444441")
    axes[0].set_ylim(0, 1.1)
    axes[1].set_ylim(0, 1.1)
    axes[1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.text(0.01, 0.01, "Paramètres synthétiques. Médiane et intervalle 10 à 90 % sur 40 tirages.", fontsize=8, color="#5F5E5A")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "scenarios.png", dpi=160, facecolor="white")
    print("\nFigure : scenarios.png")


if __name__ == "__main__":
    main()
