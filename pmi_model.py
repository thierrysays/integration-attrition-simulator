"""Modèle multi-agents minimal d'une intégration post-acquisition.

Périmètre : acquisition d'une société produit de taille moyenne par un grand
groupe, avec migration d'infrastructure et exploitation courante en parallèle.

Toutes les valeurs numériques sont SYNTHÉTIQUES. Elles traduisent des ordres de
grandeur qualitatifs, pas des données d'un cas réel. Le modèle sert à explorer
des mécanismes et des scénarios comparés, pas à produire des prévisions.

Boucles représentées
    R1  départs -> capacité -> retard -> incertitude -> départs
    R2  dette -> charge d'exploitation -> capacité -> résorption de la dette
    R3  retard -> revenu exposé -> pression -> incertitude -> départs
Leviers extérieurs (activables) : prime de rétention, budget glissant,
exploitation parallèle.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import mesa

REFERENCE_DEBT = 0.80  # niveau de dette qui fixe l'ampleur de la migration


@dataclass(frozen=True)
class Params:
    # Équipe
    n_engineers: int = 40
    key_share: float = 0.20
    key_productivity: float = 1.5
    onboarding_weeks: int = 16
    # Calendrier
    weeks: int = 156
    plan_weeks: int = 156
    # Dette et exploitation courante (maintien de l'existant + réduction de dette)
    debt0: float = 0.80
    bau_floor: float = 0.06
    bau_debt_coef: float = 0.30  # part d'exploitation = 0,06 + 0,30 x dette
    debt_split: float = 0.25  # part de la capacité libre affectée à la résorption
    debt_gain: float = 0.025
    shortcut_debt: float = 0.004  # dette créée par les raccourcis quand on est en retard
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
    def __init__(self, model: "IntegrationModel", key: bool, sens: float, joined: int):
        super().__init__(model)
        self.key = key
        self.sens = sens  # sensibilité individuelle à l'incertitude
        self.joined = joined

    def productivity(self) -> float:
        p = self.model.p
        base = p.key_productivity if self.key else 1.0
        age = self.model.week - self.joined
        ramp = 1.0 if age >= p.onboarding_weeks else 0.3 + 0.7 * age / p.onboarding_weeks
        return base * ramp

    def quit_probability(self) -> float:
        p = self.model.p
        prob = p.base_quit + p.quit_gain * self.sens * self.model.uncertainty
        if self.key and p.retention_bonus and self.model.week < p.bonus_weeks:
            prob *= 1.0 - p.bonus_efficacy
        return prob


class IntegrationModel(mesa.Model):
    def __init__(self, params: Params, seed: int | None = None):
        super().__init__(rng=seed)
        self.p = params
        self.week = 0
        self.debt = params.debt0
        self.uncertainty = params.announce_u0
        self.progress = 0.0
        self.revenue = 1.0
        self.slippage = 0.0
        self.n0 = params.n_engineers
        self.departures_key = 0
        self.departures_other = 0
        self._recent = deque([0] * 12, maxlen=12)

        n_key = round(params.n_engineers * params.key_share)
        for i in range(params.n_engineers):
            Engineer(self, key=i < n_key, sens=self.random.uniform(0.4, 1.6), joined=-10**6)

        self.e0 = sum(a.productivity() for a in self.agents)
        ref_available = self.e0 * (
            1.0
            - (params.bau_floor + params.bau_debt_coef * REFERENCE_DEBT)
            - params.parallel_overhead
        )
        self.w_total = ref_available * (1.0 - params.debt_split) * params.plan_weeks

        self.hist = {k: [] for k in ("headcount", "progress", "planned", "uncertainty", "debt", "revenue")}

    def step(self) -> None:
        p = self.p
        agents = list(self.agents)

        effort = sum(a.productivity() for a in agents)
        bau = self.e0 * (p.bau_floor + p.bau_debt_coef * self.debt)
        overhead = self.e0 * p.parallel_overhead if (p.parallel_run and self.progress < 1.0) else 0.0
        available = max(0.0, effort - bau - overhead)
        if self.progress < 1.0:
            debt_effort = p.debt_split * available
            migration_effort = available - debt_effort
        else:
            debt_effort, migration_effort = available, 0.0

        self.progress = min(1.0, self.progress + migration_effort / self.w_total)
        planned = min(1.0, (self.week + 1) / p.plan_weeks)
        self.slippage = max(0.0, planned - self.progress)

        self.debt = max(
            0.0,
            self.debt - p.debt_gain * debt_effort / self.e0 + p.shortcut_debt * self.slippage,
        )

        exposed = p.in_flight_revenue if self.progress < 1.0 else 0.0
        protect = p.parallel_efficacy if p.parallel_run else 0.0
        churn = exposed * p.churn_base * (1.0 + p.churn_slip_gain * self.slippage) * (1.0 - protect)
        self.revenue *= 1.0 - churn

        pressure = min(1.0, 4.0 * (1.0 - self.revenue))
        recent_rate = sum(self._recent) / self.n0
        announce = p.announce_u0 * pow(2.718281828, -self.week / p.announce_tau)
        target = min(
            1.0,
            announce + p.w_slip * self.slippage + p.w_rev * pressure + p.w_dep * recent_rate,
        )
        self.uncertainty += p.u_smooth * (target - self.uncertainty)

        leavers = [a for a in agents if self.random.random() < a.quit_probability()]
        for a in leavers:
            if a.key:
                self.departures_key += 1
            else:
                self.departures_other += 1
            a.remove()
        self._recent.append(len(leavers))

        headcount = len(self.agents)
        if p.rolling_budget and headcount < self.n0 and self.random.random() < p.hire_prob:
            Engineer(self, key=False, sens=self.random.uniform(0.4, 1.6), joined=self.week)

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
            "final_headcount": h[-1],
            "progress": self.progress,
            "final_slippage": self.slippage,
            "final_debt": self.debt,
            "revenue_lost": 1.0 - self.revenue,
            "departures_key": self.departures_key,
            "departures_other": self.departures_other,
            "spiral": min(h) < spiral_threshold,
        }
