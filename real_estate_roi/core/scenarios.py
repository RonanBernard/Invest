from __future__ import annotations

from typing import Dict

from .model import InvestmentInputs, RealEstateModel


def build_owner_cashflows(inputs: InvestmentInputs) -> Dict[str, object]:
    model = RealEstateModel(inputs)
    return model.run_owner()


def build_rental_cashflows(inputs: InvestmentInputs) -> Dict[str, object]:
    model = RealEstateModel(inputs)
    return model.run_rental()


