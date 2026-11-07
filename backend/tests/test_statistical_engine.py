"""
Unit Tests for CloudSage Pure Decimal Statistical Operations.
Tests Mean, Standard Deviation, Median, MAD, Quartiles, IQR, Z-Score, Modified Z-Score, and Tukey Fences.
Verifies pure Decimal precision, zero-variance handling, and hand-calculated mathematical test vectors.
"""

from decimal import Decimal
import pytest

from backend.app.anomaly_detection.statistics import (
    iqr,
    iqr_fences,
    mad,
    mean,
    median,
    modified_z_score,
    quartiles,
    stddev,
    z_score,
)


def test_mean_and_stddev_known_distribution():
    """Validates arithmetic mean and sample standard deviation against known values."""
    # Population: [10, 20, 30, 40, 50] -> Mean = 30.0000, Sample StdDev = sqrt(250) ≈ 15.8114
    data = [Decimal(str(x)) for x in [10, 20, 30, 40, 50]]
    m = mean(data)
    assert m == Decimal("30.0000")
    assert isinstance(m, Decimal)

    s = stddev(data, ddof=1)
    assert s == Decimal("15.8114")
    assert isinstance(s, Decimal)


def test_median_odd_and_even_lengths():
    """Validates median calculation for both odd and even length series."""
    odd_data = [Decimal(str(x)) for x in [12, 3, 5, 8, 20]]  # Sorted: 3, 5, 8, 12, 20 -> 8
    med_odd = median(odd_data)
    assert med_odd == Decimal("8.0000")

    even_data = [Decimal(str(x)) for x in [10, 20, 30, 40]]  # Med = (20 + 30)/2 = 25
    med_even = median(even_data)
    assert med_even == Decimal("25.0000")


def test_median_absolute_deviation_mad():
    """Validates MAD calculation: MAD = median(|x_i - median(X)|)."""
    # Series: [1, 2, 3, 4, 5, 6, 7, 8, 9] -> Median = 5
    # Absolute deviations: [4, 3, 2, 1, 0, 1, 2, 3, 4] -> Sorted: 0, 1, 1, 2, 2, 3, 3, 4, 4 -> Median = 2
    data = [Decimal(str(x)) for x in range(1, 10)]
    m = mad(data)
    assert m == Decimal("2.0000")


def test_quartiles_and_iqr():
    """Validates Q1, median, Q3, and IQR calculation."""
    # Data: [1, 2, 3, 4, 5, 6, 7, 8]
    # Lower half: [1, 2, 3, 4] -> Q1 = (2 + 3)/2 = 2.5
    # Median = (4 + 5)/2 = 4.5
    # Upper half: [5, 6, 7, 8] -> Q3 = (6 + 7)/2 = 6.5
    # IQR = 6.5 - 2.5 = 4.0
    data = [Decimal(str(x)) for x in range(1, 9)]
    q1_val, med_val, q3_val = quartiles(data)
    assert q1_val == Decimal("2.5000")
    assert med_val == Decimal("4.5000")
    assert q3_val == Decimal("6.5000")

    iqr_val = iqr(data)
    assert iqr_val == Decimal("4.0000")


def test_tukey_fences():
    """Validates Tukey fences: Lower = Q1 - 1.5*IQR, Upper = Q3 + 1.5*IQR."""
    q1 = Decimal("100.0000")
    q3 = Decimal("200.0000")
    iqr_val = Decimal("100.0000")

    lower, upper = iqr_fences(q1, q3, iqr_val, multiplier=Decimal("1.5000"))
    assert lower == Decimal("-50.0000")
    assert upper == Decimal("350.0000")


def test_z_score_calculation():
    """Validates standard parametric score: z = (x - mu) / sigma."""
    mu = Decimal("100.0000")
    sigma = Decimal("20.0000")
    val = Decimal("160.0000")

    zs = z_score(val, mu, sigma)
    # (160 - 100) / 20 = 3.0000
    assert zs == Decimal("3.0000")


def test_modified_z_score_calculation():
    """Validates Boris Iglewicz and David Hoaglin Modified Z-Score: M_i = 0.6745 * (x_i - med) / MAD."""
    med = Decimal("50.0000")
    mad_val = Decimal("10.0000")
    val = Decimal("100.0000")

    # M_i = 0.6745 * (100 - 50) / 10 = 0.6745 * 5 = 3.3725
    mzs = modified_z_score(val, med, mad_val)
    assert mzs == Decimal("3.3725")


def test_zero_variance_safeguards():
    """Verifies that flat distributions (sigma = 0, MAD = 0) do not cause DivisionByZero."""
    flat_data = [Decimal("100.0000")] * 10
    m = mean(flat_data)
    s = stddev(flat_data)
    med = median(flat_data)
    mad_val = mad(flat_data)

    assert m == Decimal("100.0000")
    assert s == Decimal("0.0000")
    assert med == Decimal("100.0000")
    assert mad_val == Decimal("0.0000")

    zs = z_score(Decimal("150.0000"), m, s)
    assert zs == Decimal("0.0000")

    mzs = modified_z_score(Decimal("150.0000"), med, mad_val)
    assert mzs == Decimal("0.0000")


def test_empty_and_single_element_inputs():
    """Validates graceful handling of empty lists and single element series."""
    assert mean([]) == Decimal("0.0000")
    assert stddev([]) == Decimal("0.0000")
    assert stddev([Decimal("42.0000")]) == Decimal("0.0000")
    assert median([]) == Decimal("0.0000")
    assert mad([]) == Decimal("0.0000")
    q1, med_val, q3 = quartiles([])
    assert q1 == Decimal("0.0000")
