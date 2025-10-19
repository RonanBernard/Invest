from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict

# Project root (parent of this file)
BASE_DIR = Path(__file__).resolve().parent


def _load_yaml() -> Dict[str, Any]:
    with open(BASE_DIR / "config.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        return data


CFG = _load_yaml()

# Purchase & costs
PRICE: float = float(CFG["price"])
NOTARY_PCT: float = float(CFG["notary_pct"]) / 100.0
AGENCY_PCT: float = float(CFG["agency_pct"]) / 100.0
RENOVATION_COSTS: float = float(CFG["renovation_costs"])
EXTRA_FEES: float = float(CFG["extra_fees"])

# Loan
LOAN_RATE: float = float(CFG["loan_rate"]) / 100.0
LOAN_YEARS: int = int(CFG["loan_years"])
DOWN_PAYMENT: float = float(CFG["down_payment"])

# Recurring costs
PROPERTY_TAX_ANNUAL: float = float(CFG["property_tax_annual"])
OTHER_TAXES_ANNUAL: float = float(CFG["other_taxes_annual"])
INSURANCE_RATE_ON_INITIAL_PER_YEAR: float = float(CFG["insurance_rate_on_initial_per_year"]) / 100.0
COPRO_CHARGES_ANNUAL: float = float(CFG["copro_charges_annual"])
COPRO_GROWTH_RATE: float = float(CFG["copro_growth_rate"]) / 100.0
MAINTENANCE_RATE_OF_VALUE: float = float(CFG["maintenance_rate_of_value"]) / 100.0

# Growth & timeline
BENCHMARK_RETURN_RATE: float = float(CFG["benchmark_return_rate"]) / 100.0
PRICE_GROWTH_RATE: float = float(CFG["price_growth_rate"]) / 100.0
INFLATION_RATE: float = float(CFG["inflation_rate"]) / 100.0
INVEST_DURATION: int = int(CFG["invest_duration"])

# Rental specific
OCCUPANCY_RATE: float = float(CFG["occupancy_rate"])  # already 0..1
RENT_MONTHLY: float = float(CFG["rent_monthly"])
RENT_GROWTH_RATE: float = float(CFG["rent_growth_rate"]) / 100.0
MANAGEMENT_FEE_RATE: float = float(CFG["management_fee_rate"]) / 100.0
RENTAL_TAX_RATE: float = float(CFG["rental_tax_rate"]) / 100.0

# Exit costs/taxes
SELLING_FEES_RATE: float = float(CFG["selling_fees_rate"]) / 100.0
CAPITAL_GAINS_EFF_RATE: float = float(CFG["capital_gains_eff_rate"]) / 100.0
INCLUDE_EARLY_REPAYMENT_PENALTY: bool = bool(CFG["include_early_repayment_penalty"])
BENCHMARK_RENT_MONTHLY: float = float(CFG["benchmark_rent_monthly"])