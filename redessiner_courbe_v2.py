"""Redessine distance_seuil_v2.png à partir de resultats_v2_courbe.csv, sans relancer
les simulations. Usage : python3 redessiner_courbe_v2.py
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).parent
with open(OUT / "resultats_v2_courbe.csv") as f:
    rows = list(csv.DictReader(f))
mults = [float(r["multiple"]) for r in rows]
col = lambda k: [float(r[k]) for r in rows]

style = {
    "freelance_distribue_base": ("#0F6E56", "-", "Freelance distribué, trois leviers"),
    "freelance_distribue_nolev": ("#A32D2D", "-", "Freelance distribué, sans levier"),
    "freelance_regroupe_base": ("#0F6E56", "--", "Freelance regroupé, trois leviers"),
    "freelance_regroupe_nolev": ("#A32D2D", "--", "Freelance regroupé, sans levier"),
    "salaries_regroupes_base": ("#0F6E56", ":", "Salariés regroupés, trois leviers"),
    "salaries_regroupes_nolev": ("#A32D2D", ":", "Salariés regroupés, sans levier"),
}

fig, ax = plt.subplots(figsize=(8.3, 5.0))
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color("#888780")
    ax.spines[s].set_linewidth(0.6)
ax.grid(axis="y", color="#D3D1C7", linewidth=0.5)
ax.tick_params(colors="#444441", labelsize=9)
for k, (color, ls, label) in style.items():
    ax.plot(mults, col(k), color=color, linestyle=ls, linewidth=1.7, marker="o", markersize=3.5, label=label)
ax.set_xscale("log", base=2)
ax.set_xticks(mults)
ax.set_xticklabels([f"x{m:g}" for m in mults])
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
print("Figure : distance_seuil_v2.png")
