# Calculateur de rentabilité immobilière

Projet Python complet : moteur de calcul (amortissement, cashflows, IRR/NPV) + UI Streamlit.

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
# depuis la racine du repo
pip install -r real_estate_roi/requirements.txt
```

## Lancement

```bash
# exécuter depuis la racine du repo
streamlit run real_estate_roi/app/streamlit_app.py
```

L'application lit ses valeurs par défaut dans `config.yaml` à la racine du dépôt (voir ci-dessous).

## Configuration (config.yaml)

Fichier: `config.yaml` (racine du dépôt). Toutes les clés sont obligatoires.

- price, renovation_costs, extra_fees, property_tax_annual, other_taxes_annual, rent_monthly, benchmark_rent_monthly: montants en €
- loan_years, invest_duration: entiers (années)
- Pourcentages saisis en pourcents (0–100): notary_pct, agency_pct, loan_rate, insurance_rate_on_initial_per_year, copro_growth_rate, maintenance_rate_of_value, benchmark_return_rate, price_growth_rate, inflation_rate, rent_growth_rate, management_fee_rate, rental_tax_rate, selling_fees_rate, capital_gains_eff_rate
- occupancy_rate: proportion 0–1
- include_early_repayment_penalty: booléen

Exemple minimal:

```yaml
price: 250000.0
notary_pct: 7.5
agency_pct: 3
loan_rate: 3
loan_years: 20
down_payment: 50000.0
property_tax_annual: 1200.0
other_taxes_annual: 0.0
insurance_rate_on_initial_per_year: 0.25
copro_charges_annual: 1200.0
copro_growth_rate: 2
maintenance_rate_of_value: 1
benchmark_return_rate: 5
price_growth_rate: 2
inflation_rate: 2
invest_duration: 10
occupancy_rate: 0.92
rent_monthly: 1100.0
rent_growth_rate: 2
management_fee_rate: 6
rental_tax_rate: 30
selling_fees_rate: 5
capital_gains_eff_rate: 0
include_early_repayment_penalty: false
benchmark_rent_monthly: 800.0
```

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
