# Calculateur de rentabilité immobilière

Projet Python complet : moteur de calcul (amortissement, cashflows, IRR/NPV) + UI Streamlit.

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app/streamlit_app.py
```

Conseil: exécuter la commande depuis le dossier `real_estate_roi/` pour que le package soit importable.

## Tests

```bash
pytest -q
```

## Principales formules
- Mensualité crédit: M = P · i(1+i)^n / ((1+i)^n - 1)
- NPV: somme des flux actualisés
- IRR: racine NPV=0 (méthode bissection)

## Limitations & simplifications
- Fiscalité modélisée via taux effectifs.
- Assurance emprunteur approximée (% du capital initial/an).
- Frais de vente et plus-value appliqués de manière simplifiée.

## Exemple
Voir `examples/scenario_exemple.json`.
