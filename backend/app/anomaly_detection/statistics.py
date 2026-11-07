"""
CloudSage Pure Decimal Statistical Operations.
Provides deterministic, non-floating-point implementations of Mean, Standard Deviation,
Median, MAD, Quartiles, IQR, Z-Score, Modified Z-Score, and Tukey Fences.
Zero float representations permitted.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple


PRECISION_FOUR = Decimal("0.0001")


def mean(values: List[Decimal]) -> Decimal:
    """Calculates arithmetic mean with Decimal precision."""
    if not values:
        return Decimal("0.0000")
    total = sum(values, Decimal("0.0000"))
    return (total / Decimal(str(len(values)))).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)


def stddev(values: List[Decimal], ddof: int = 1) -> Decimal:
    """
    Calculates sample standard deviation with Decimal precision.
    Returns 0.0000 if len(values) <= ddof.
    """
    n = len(values)
    if n <= ddof:
        return Decimal("0.0000")

    mu = mean(values)
    sum_sq_diff = sum(((x - mu) ** 2 for x in values), Decimal("0.0000"))
    variance = sum_sq_diff / Decimal(str(n - ddof))
    if variance <= Decimal("0.0000"):
        return Decimal("0.0000")

    return variance.sqrt().quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)


def median(values: List[Decimal]) -> Decimal:
    """Calculates median of sorted Decimal values."""
    if not values:
        return Decimal("0.0000")

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2

    if n % 2 == 1:
        return sorted_vals[mid].quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
    else:
        med = (sorted_vals[mid - 1] + sorted_vals[mid]) / Decimal("2.0")
        return med.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)


def mad(values: List[Decimal]) -> Decimal:
    """
    Calculates Median Absolute Deviation (MAD):
    MAD = median(|x_i - median(X)|)
    """
    if not values:
        return Decimal("0.0000")

    med = median(values)
    abs_deviations = [abs(x - med) for x in values]
    return median(abs_deviations)


def quartiles(values: List[Decimal]) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculates first quartile (Q1), median (Q2), and third quartile (Q3).
    Uses standard Tukey hinge / percentile method with Decimal precision.
    """
    if not values:
        zero = Decimal("0.0000")
        return zero, zero, zero

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    med = median(sorted_vals)

    if n == 1:
        v = sorted_vals[0].quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
        return v, v, v

    mid = n // 2
    if n % 2 == 0:
        lower_half = sorted_vals[:mid]
        upper_half = sorted_vals[mid:]
    else:
        lower_half = sorted_vals[:mid]
        upper_half = sorted_vals[mid + 1:]

    q1 = median(lower_half) if lower_half else sorted_vals[0]
    q3 = median(upper_half) if upper_half else sorted_vals[-1]

    return (
        q1.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
        med.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
        q3.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
    )


def iqr(values: List[Decimal]) -> Decimal:
    """Calculates Interquartile Range (IQR = Q3 - Q1)."""
    q1, _, q3 = quartiles(values)
    return (q3 - q1).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)


def z_score(observed: Decimal, mean_val: Decimal, stddev_val: Decimal) -> Decimal:
    """
    Calculates standard Z-Score:
    Z = (observed - mean) / stddev
    Returns 0.0000 when stddev is 0.
    """
    if stddev_val <= Decimal("0.0000"):
        return Decimal("0.0000")
    delta = observed - mean_val
    return (delta / stddev_val).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)


def modified_z_score(observed: Decimal, median_val: Decimal, mad_val: Decimal) -> Decimal:
    """
    Calculates robust Boris Iglewicz and David Hoaglin Modified Z-Score:
    Modified Z = 0.6745 * (observed - median) / MAD
    Returns 0.0000 when MAD is 0.
    """
    if mad_val <= Decimal("0.0000"):
        return Decimal("0.0000")
    delta = observed - median_val
    factor = Decimal("0.6745")
    return ((factor * delta) / mad_val).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)


def iqr_fences(
    q1: Decimal,
    q3: Decimal,
    iqr_val: Optional[Decimal] = None,
    multiplier: Decimal = Decimal("1.5"),
) -> Tuple[Decimal, Decimal]:
    """
    Calculates Tukey lower and upper fences:
    Lower = Q1 - (multiplier * IQR)
    Upper = Q3 + (multiplier * IQR)
    """
    effective_iqr = iqr_val if iqr_val is not None else (q3 - q1)
    lower = q1 - (multiplier * effective_iqr)
    upper = q3 + (multiplier * effective_iqr)
    return (
        lower.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
        upper.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
    )
