from __future__ import annotations

def rental_effective_tax(income: float, rate: float) -> float:
    """Compute effective rental tax.

    Applies the effective tax rate to positive rental income only.
    """
    if rate <= 0 or income <= 0:
        return 0.0
    return income * rate


def capital_gains_tax(gain: float, eff_rate: float) -> float:
    """Compute effective capital gains tax.

    Negative gains are not taxed.
    """
    if eff_rate <= 0 or gain <= 0:
        return 0.0
    return gain * eff_rate


