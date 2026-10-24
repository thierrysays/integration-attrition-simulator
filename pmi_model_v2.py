"""Modèle multi-agents d'intégration post-acquisition, version 2.

Ajouts par rapport à pmi_model.py (conservé tel quel) :
  1. Équipe mixte salariés et freelances. Un freelance ne peut partir qu'à une
     échéance de contrat (tous les contract_weeks semaines). Une part
     sync_share des contrats initiaux partage la même échéance, ce qui concentre
     les départs possibles dans le temps.
  2. Perte de connaissance. Chaque personne accumule de la connaissance de la
     migration (plafonnée à 52 semaines d'ancienneté). Un départ ajoute au
     travail restant un volume proportionnel à cette connaissance. Une
     personne clé en porte key_knowledge fois plus.

Toutes les valeurs numériques sont SYNTHÉTIQUES.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import mesa

REFERENCE_DEBT = 0.80


@dataclass(frozen=True)
class Params:
    # Équipe
    n_engineers: int = 40
    key_share: float = 0.20
    key_productivity: float = 1.5
    onboarding_weeks: int = 16
    freelance_share: float = 0.65
    contract_weeks: int = 26
    sync_share: float = 0.50
    key_knowledge: float = 3.0
    rework_factor: float = 20.0  # semaines-personnes de reprise par unité de connaissance
    coordination_penalty: float = 0.0  # part d'effort perdue en coordination (équipe distribuée)
    # Calendrier
    weeks: int = 156
    plan_weeks: int = 156
    # Dette et exploitation courante
    debt0: float = 0.80
    bau_floor: float = 0.06
    bau_debt_coef: float = 0.30
    debt_split: float = 0.25
    debt_gain: float = 0.025
    shortcut_debt: float = 0.004
    # Exploitation parallèle et revenu
    parallel_overhead: float = 0.08
    parallel_efficacy: float = 0.95
    in_flight_revenue: float = 0.15
    churn_base: float = 0.004
    churn_slip_gain: float = 10.0
    # Incertitude perçue
    announce_u0: float = 0.50
    announce_tau: float = 26.0
    w_slip: float = 1.5
    w_rev: float = 1.0
    w_dep: float = 3.0
    u_smooth: float = 0.15
    # Départs et embauches
    base_quit: float = 0.002
    quit_gain: float = 0.012
    bonus_efficacy: float = 0.85
    bonus_weeks: int = 104
    hire_prob: float = 0.30
    # Leviers
    retention_bonus: bool = True
    rolling_budget: bool = True
    parallel_run: bool = True


class Engineer(mesa.Agent):
    def __init__(self, model, key, sens, joined, freelance, offset):
        super().__init__(model)
        self.key = key
        self.sens = sens
        self.joined = joined
        self.freelance = freelance
        self.offset = offset

    def productivity(self) -> float:
        p = self.model.p
        base = p.key_productivity if self.key else 1.0
        age = self.model.week - self.joined
        ramp = 1.0 if age >= p.onboarding_weeks else 0.3 + 0.7 * age / p.onboarding_weeks
        return base * ramp

    def knowledge(self) -> float:
        p = self.model.p
        tenure = min(52, max(0, self.model.week - max(self.joined, 0)))
        return (p.key_knowledge if self.key else 1.0) * tenure / 52.0

    def weekly_hazard(self) -> float:
        p = self.model.p
        h = p.base_quit + p.quit_gain * self.sens * self.model.uncertainty
        if self.key and p.retention_bonus and self.model.week < p.bonus_weeks:
            h *= 1.0 - p.bonus_efficacy
        return min(1.0, h)

    def leaves_now(self) -> bool:
        p = self.model.p
        h = self.weekly_hazard()
        if not self.freelance:
            return self.model.random.random() < h
        if self.model.week == 0 or (self.model.week - self.offset) % p.contract_weeks != 0:
            return False
        return self.model.random.random() < 1.0 - (1.0 - h) ** p.contract_weeks


class IntegrationModel(mesa.Model):
    def __init__(self, params: Params, seed: int | None = None):
        super().__init__(rng=seed)
        self.p = params
        self.week = 0
        self.debt = params.debt0
        self.uncertainty = params.announce_u0
        self.work_done = 0.0
        self.rework = 0.0
        self.done = False
        self.progress = 0.0
        self.revenue = 1.0
        self.slippage = 0.0
        self.n0 = params.n_engineers
        self.departures_key = 0
        self.departures_other = 0
        self._recent = deque([0] * 12, maxlen=12)

        n_key = round(params.n_engineers * params.key_share)
        for i in range(params.n_engineers):
            freelance = self.random.random() < params.freelance_share
            offset = 0 if self.random.random() < params.sync_share else self.random.randrange(params.contract_weeks)
            Engineer(self, key=i < n_key, sens=self.random.uniform(0.4, 1.6),
                     joined=-10**6, freelance=freelance, offset=offset)

        self.e0 = sum(a.productivity() for a in self.agents)
        ref_available = self.e0 * (
            1.0 - (params.bau_floor + params.bau_debt_coef * REFERENCE_DEBT) - params.parallel_overhead
        )
        self.w_total = ref_available * (1.0 - params.debt_split) * params.plan_weeks
        self.hist = {k: [] for k in ("headcount", "progress", "planned", "uncertainty", "debt", "revenue")}

    def step(self) -> None:
        p = self.p
        agents = list(self.agents)

        effort = sum(a.productivity() for a in agents) * (1.0 - p.coordination_penalty)
        bau =self.e0 * (p.bau_floor + p.bau_debt_coef * self.debt)
        overhead = self.e0 * p.parallel_overhead if (p.parallel_run and not self.done) else 0.0
        available = max(0.0, effort - bau - overhead)
        if not self.done:
            debt_effort = p.debt_split * available
            migration_effort = available - debt_effort
        else:
            debt_effort, migration_effort = available, 0.0

        self.work_done += migration_effort
        if not self.done:
            total = self.w_total + self.rework
            if self.work_done >= total:
                self.done = True
                self.progress = 1.0
            else:
                self.progress = self.work_done / total
        planned = min(1.0, (self.week + 1) / p.plan_weeks)
        self.slippage = max(0.0, planned - self.progress)

        self.debt = max(
            0.0, self.debt - p.debt_gain * debt_effort / self.e0 + p.shortcut_debt * self.slippage
        )

        exposed = p.in_flight_revenue if not self.done else 0.0
        protect = p.parallel_efficacy if p.parallel_run else 0.0
        churn = exposed * p.churn_base * (1.0 + p.churn_slip_gain * self.slippage) * (1.0 - protect)
        self.revenue *= 1.0 - churn

        pressure = min(1.0, 4.0 * (1.0 - self.revenue))
        recent_rate = sum(self._recent) / self.n0
        announce = p.announce_u0 * pow(2.718281828, -self.week / p.announce_tau)
        target = min(1.0, announce + p.w_slip * self.slippage + p.w_rev * pressure + p.w_dep * recent_rate)
        self.uncertainty += p.u_smooth * (target - self.uncertainty)

        leavers = [a for a in agents if a.leaves_now()]
        for a in leavers:
            if a.key:
                self.departures_key += 1
            else:
                self.departures_other += 1
            if not self.done:
                self.rework += p.rework_factor * a.knowledge()
            a.remove()
        self._recent.append(len(leavers))

        if p.rolling_budget and len(self.agents) < self.n0 and self.random.random() < p.hire_prob:
            Engineer(self, key=False, sens=self.random.uniform(0.4, 1.6), joined=self.week,
                     freelance=self.random.random() < p.freelance_share,
                     offset=self.week % p.contract_weeks)

        self.week += 1
        self.hist["headcount"].append(len(self.agents) / self.n0)
        self.hist["progress"].append(self.progress)
        self.hist["planned"].append(planned)
        self.hist["uncertainty"].append(self.uncertainty)
        self.hist["debt"].append(self.debt)
        self.hist["revenue"].append(self.revenue)

    def run(self) -> "IntegrationModel":
        for _ in range(self.p.weeks):
            self.step()
        return self

    def summary(self, spiral_threshold: float = 0.60) -> dict:
        h = self.hist["headcount"]
        return {
            "min_headcount": min(h),
            "progress": self.progress,
            "final_debt": self.debt,
            "revenue_lost": 1.0 - self.revenue,
            "departures_key": self.departures_key,
            "departures_other": self.departures_other,
            "rework_share": self.rework / self.w_total,
            "spiral": min(h) < spiral_threshold,
        }
