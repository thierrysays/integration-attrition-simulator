# Integration attrition simulator / Simulateur d'attrition d'intégration

Agent-based model of a post-acquisition integration: a team of 40 engineers, a 156-week migration, ongoing operations running in parallel, and departures that feed back on schedule and uncertainty. All numerical values are **synthetic**. The model explores mechanisms and compares scenarios. It produces no forecast. The reference case is anonymised.

Modèle à base d'agents d'une intégration post-acquisition : une équipe de 40 ingénieurs, une migration de 156 semaines, l'exploitation courante menée en parallèle, et des départs qui rétroagissent sur le calendrier et l'incertitude. Toutes les valeurs numériques sont **synthétiques**. Le modèle explore des mécanismes et compare des scénarios. Il ne produit aucune prévision. Le cas de référence est anonymisé.

## Install / Installation

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10 or later. Tested with Mesa 3.5.1 and Matplotlib 3.11. / Python 3.10 ou plus récent. Testé avec Mesa 3.5.1 et Matplotlib 3.11.

## Files / Fichiers

| File / Fichier | Role / Rôle |
|---|---|
| `pmi_model.py` | Version 1 of the model: three feedback loops and three external levers / Version 1 : trois boucles de rétroaction, trois leviers extérieurs |
| `pmi_model_v2.py` | Version 2: freelance and salaried staff, knowledge loss on departure / Version 2 : freelances et salariés, perte de connaissance au départ |
| `run_scenarios.py` | Version 1 scenarios and lever ablation / Scénarios de la version 1 et retrait des leviers |
| `calibrer_attrition.py` | Calibrates attrition on an observed number of departures / Calibre l'attrition sur un nombre de départs observé |
| `tracer_seuil.py` | Tipping curve, version 1 / Courbe de basculement, version 1 |
| `run_v2.py` | Version 2: three team structures, tipping curve / Version 2 : trois structures d'équipe, courbe de basculement |
| `redessiner_courbe_v2.py` | Redraws the version 2 figure from the CSV without rerunning / Redessine la figure de la version 2 depuis le CSV |
| `resultats/` | CSV outputs / Résultats au format CSV |
| `figures/` | Figures (French labels) / Figures (libellés en français) |
| `LICENSE`, `NOTICE`, `LICENSE-DATA.md` | Licences / Licences |

## Run / Exécution

```
python3 run_scenarios.py
python3 calibrer_attrition.py
python3 tracer_seuil.py
python3 run_v2.py
```

Each script writes its CSV and figure next to itself. Move them into `resultats/` and `figures/` if you want the same layout. Seeds are fixed, so a rerun reproduces the published numbers. Allow several minutes for `run_v2.py`. / Chaque script écrit son CSV et sa figure à côté de lui. Les graines sont fixées : une nouvelle exécution reproduit les chiffres publiés. Prévoir plusieurs minutes pour `run_v2.py`.

## Limits / Limites

One reference case, synthetic parameters, 40 people, 60 draws per point. The tipping threshold depends on the calibration and on the team structure. It is a distance to compare, not a value to apply. / Un seul cas de référence, des paramètres synthétiques, 40 personnes, 60 tirages par point. Le seuil de basculement dépend du calibrage et de la structure de l'équipe : c'est une distance à comparer, pas une valeur à appliquer.

## Licence

Code: Apache License 2.0 (`LICENSE`, `NOTICE`). Results, figures and this README: CC BY 4.0 (`LICENSE-DATA.md`). Attribution: Thierry Sayegh-Sauvage. / Code : Apache License 2.0 (`LICENSE`, `NOTICE`). Résultats, figures et cette notice : CC BY 4.0 (`LICENSE-DATA.md`). Attribution : Thierry Sayegh-Sauvage.

Thierry Sayegh-Sauvage · thierry@glossolalie.pro · linkedin.com/in/thierrys
