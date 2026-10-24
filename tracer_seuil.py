"""Courbe de basculement : taux de spirale selon l'attrition, en multiples du cas observé.

Facteurs issus de calibrer_attrition.py : lecture A (3 départs sur trois ans) = 0,1695,
lecture B (3 départs par an) = 0,4609, soit environ 2,7 fois la lecture A.
Usage : python3 tracer_seuil.py
"""
from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from calibrer_attrition import scaled
from run_scenarios import REFERENCE, agg, run_many

OUT = Path(__file__).parent
S_A, S_B = 0.1695, 0.4609
MULTS = [1, 1.5, 2, 3, 4, 6, 8, 12, 16]

rows = []
for m in MULTS:
    p = scaled(REFERENCE, S_A * m)
    base = agg(run_many(p, n=60))["spiral_rate"]
    none = agg(run_many(replace(p, retention_bonus=False, rolling_budget=False, parallel_run=False), n=60))["spiral_rate"]
    rows.append((m, base, none))
    print(f"x{m:<5} base {base:5.0%}   sans levier {none:5.0%}")

with open(OUT / "resultats_courbe_seuil.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["multiple_attrition_observee", "spirale_base", "spirale_sans_levier"])
    w.writerows([[m, round(b, 3), round(n, 3)] for m, b, n in rows])

fig, ax = plt.subplots(figsize=(8.3, 4.2))
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color("#888780")
    ax.spines[s].set_linewidth(0.6)
ax.grid(axis="y", color="#D3D1C7", linewidth=0.5)
ax.tick_params(colors="#444441", labelsize=9)
xs = [r[0] for r in rows]
ax.plot(xs, [r[1] for r in rows], color="#0F6E56", linewidth=1.8, marker="o", markersize=4, label="Avec les trois leviers")
ax.plot(xs, [r[2] for r in rows], color="#A32D2D", linewidth=1.8, marker="o", markersize=4, label="Sans aucun levier")
ax.set_xscale("log", base=2)
ax.set_xticks(MULTS)
ax.set_xticklabels([f"x{m:g}" for m in MULTS])
ax.set_ylim(-0.03, 1.05)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_yticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])
ax.axvline(1, color="#444441", linewidth=0.8, linestyle="--")
ax.axvline(S_B / S_A, color="#444441", linewidth=0.8, linestyle=":")
ax.text(1.03, 0.93, "Lecture A\n3 départs sur 3 ans", fontsize=8, color="#444441", va="top")
ax.text(S_B / S_A * 1.03, 0.30, "Lecture B\n3 départs par an", fontsize=8, color="#444441", va="top")
ax.set_xlabel("Attrition hors personnes clés, en multiples du cas observé (lecture A)", fontsize=9, color="#444441")
ax.set_ylabel("Part des tirages en spirale", fontsize=9, color="#444441")
ax.set_title("Distance au seuil de basculement", fontsize=10, loc="left", color="#2C2C2A")
ax.legend(frameon=False, fontsize=8, loc="center right")
fig.text(0.01, 0.01, "Paramètres synthétiques, équipe de 40. 60 tirages par point.", fontsize=8, color="#5F5E5A")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(OUT / "distance_seuil.png", dpi=160, facecolor="white")
print("Figure : distance_seuil.png")
