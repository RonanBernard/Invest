# 🏠 Prompt complet pour Cursor – Calculateur de rentabilité immobilière

Tu es un expert en ingénierie logicielle (Python, data viz, finance immobilière) chargé de créer un projet prêt à l’emploi.  
Objectif : un **moteur de calcul de rentabilité immobilière** + **une page web Streamlit** pour saisir les variables et afficher résultats & graphiques, en comparant 3 scénarios :
1. Achat en **résidence principale** (on y habite)  
2. Achat pour **location** (investissement locatif)  
3. **Benchmark** : l’**apport** placé ailleurs à **x %/an** (capitalisation composée)

---

## ⚙️ Exigences techniques

- Python 3.11+
- Streamlit pour l’UI (`streamlit`)
- Calculs et tableaux avec `pandas`, `numpy`
- Graphiques avec `plotly`
- Typage (`typing`), docstrings NumPy, style PEP8
- Tests unitaires (`pytest`)
- Packaging : `requirements.txt` ou `pyproject.toml`
- README clair avec mode d’emploi
- Exemple de scénario (`examples/scenario_exemple.json`)
- Export CSV + PNG + rapport PDF simple (via `reportlab` ou `weasyprint`)

---

## 📁 Arborescence souhaitée

real_estate_roi/
  app/
    streamlit_app.py
  core/
    __init__.py
    model.py
    amortization.py
    taxes.py
    scenarios.py
    plots.py
    utils.py
  tests/
    test_model.py
    test_amortization.py
    test_scenarios.py
  examples/
    scenario_exemple.json
  README.md
  requirements.txt
  pyproject.toml (optionnel si poetry)


---

## 🧮 Variables d’entrée (paramétrables dans l’UI)

- Prix d’achat du bien  
- Frais de notaire (% du prix)  
- Frais d’agence (% du prix)  
- Travaux de rénovation  
- Frais annexes  
- Taux du crédit immobilier  
- Durée du crédit  
- Apport personnel  
- Taxe foncière  
- Autres impôts ou taxes  
- Assurance  
- Charges de copropriété  
- Entretien et réparations  
- Taux de rendement de l’apport si autre investissement  
- Évolution annuelle des prix de l’immobilier  
- Année d’achat / Année de vente  

**Si location :**
- Taux d’occupation  
- Revenus locatifs (mensuels)  
- Évolution des charges  
- Croissance du loyer  
- Frais de gestion locative (%)  
- Taux effectif d’imposition locative (%)  

---

## 💰 Calculs à implémenter

### 1. Crédit immobilier
- Mensualité fixe (amortissement classique) :
  \[
  M = P \cdot \frac{i(1+i)^n}{(1+i)^n - 1}
  \]
  - \( P \) = capital emprunté  
  - \( i \) = taux mensuel  
  - \( n \) = nb total de mensualités  
- Générer tableau d’amortissement mensuel et agrégé par année.

---

### 2. Coûts initiaux
- Frais de notaire = % * prix  
- Frais d’agence = % * prix  
- Travaux, frais annexes  
- Apport personnel déduit  
- Total initial = somme – apport  

---

### 3. Dépenses récurrentes
- Taxe foncière  
- Charges de copro + évolution annuelle  
- Entretien (% valeur bien/an ou forfait €/an)  
- Assurance emprunteur (% du capital initial/an ou €/mois)

---

### 4. Revenus locatifs
- Loyer annuel brut = loyer_mensuel × 12 × taux_occupation  
- Croissance annuelle du loyer  
- Déduction des frais de gestion (%)  
- Revenu net = loyers – charges – entretien – impôts  

---

### 5. Fiscalité
- Taux d’imposition effectif sur le revenu locatif (paramètre unique)  
- Impôt sur la plus-value (taux effectif) paramétrable  
- Frais de vente (% du prix de vente)  

---

### 6. Valorisation & vente
- Prix de vente = prix_achat × (1 + croissance_immo)^N  
- Produit net de vente = prix_vente – frais_vente – CRD – impôt_PV  
- Indicateurs :
  - IRR (taux de rentabilité interne)
  - NPV (valeur actuelle nette)
  - Multiplicateur de capital
  - Cash-on-cash annuel  

---

### 7. Benchmark “apport investi à x %”
- Croissance composée annuelle :
  \[
  A_N = Apport \times (1 + r)^N
  \]
- Comparer la valeur finale avec celle du projet immobilier.

---

### 8. Cashflows & patrimoine
- Construire flux de trésorerie annuels :
  - **Résidence principale** : sorties (mensualités, taxes, charges)  
  - **Location** : entrées (loyers nets) – sorties  
- Ajouter le produit de la vente  
- Calculer le **patrimoine net** année par année :
  \[
  Patrimoine = Valeur\_bien - CRD + trésorerie\_cumulée
  \]

---

## 📊 Visualisations (Plotly)

1. **Barres empilées – Cashflow annuel**
2. **Courbe – Patrimoine net cumulé** (RP / Location / Benchmark)
3. **Waterfall – Détail flux année de vente**
4. **Sensibilité** : IRR selon taux crédit / croissance immo / rendement apport

---

## 🧩 Structure du code

### `core/amortization.py`
- `amort_schedule(principal, annual_rate, years) -> pd.DataFrame`  
  → colonnes : month, payment, interest, principal, balance

### `core/taxes.py`
- `rental_effective_tax(income, rate)`
- `capital_gains_tax(gain, eff_rate)`

### `core/model.py`
- `@dataclass InvestmentInputs`  
- `class RealEstateModel:`
  - `run_owner()`
  - `run_rental()`
  - `benchmark_apport()`
  - `sale_proceeds(year)`
  - `irr()`, `npv()`

### `core/scenarios.py`
- Construit les flux de trésorerie selon les inputs

### `core/plots.py`
- Fonctions générant les graphiques Plotly

### `core/utils.py`
- Helpers : validations, croissance, format €

---

## 🧪 Tests (`pytest`)
- Vérif : mensualité connue, cohérence du capital, IRR simple, cohérence produit net de vente, croissance loyers/charges.

---

## 📈 Valeurs par défaut (exemple)

| Paramètre | Valeur |
|------------|--------|
| Prix | 250 000 € |
| Notaire | 7,5 % |
| Agence | 3 % |
| Travaux | 10 000 € |
| Frais annexes | 2 000 € |
| Taux crédit | 4,0 % |
| Durée | 25 ans |
| Apport | 50 000 € |
| Taxe foncière | 1 200 €/an |
| Assurance | 0,25 % du capital initial/an |
| Charges copro | 1 200 €/an (2 %/an) |
| Entretien | 1 % de la valeur/an |
| Rendement apport | 5 %/an |
| Évolution prix immo | 2 %/an |
| Année achat / vente | 2026 / 2036 |
| Loyer | 1 100 €/mois |
| Occupation | 92 % |
| Croissance loyer | 2 % |
| Frais gestion | 6 % |
| Fiscalité locative | 30 % |
| Frais de vente | 5 % |
| Impôt plus-value | 0 % (RP) |

---

## 🖥️ Page Streamlit (`app/streamlit_app.py`)

- **Sidebar** : tous les inputs (avec valeurs par défaut, tooltips)
- **Onglets** :
  1. Résumé
  2. Graphiques
  3. Tableaux
  4. Sensibilité
  5. Paramètres fiscaux
- **Résumé** :
  - KPIs : mensualité, cashflow net, IRR, NPV, patrimoine final, produit net de vente, benchmark apport
- **Graphiques** : afficher 1 & 2 ci-dessus + export PNG
- **Tableaux** : amortissement, cashflows, hypothèses, export CSV
- **Sensibilité** : sliders ±2 pts (taux crédit, immo, rendement apport)
- **Rapport** : export PDF ou HTML avec résumé + graphiques
- **Avertissements** :
  - Calculs simplifiés, taux effectifs à ajuster selon la situation
  - Message si année de vente < année achat + 2 ans

---

## 📦 Livrables

1. Code complet selon l’arborescence  
2. `README.md` avec :
   - Installation
   - Lancement (`streamlit run app/streamlit_app.py`)
   - Formules principales
   - Limites & simplifications  
3. Exemple JSON avec valeurs par défaut  
4. Tests unitaires `pytest` passants

---

## ✅ Objectif final

Crée le projet complet, clair, commenté, prêt à exécuter :
