import math

import pytest

from core.data_validation import require_finite_number, require_positive_finite


def test_require_finite_number_accepts_finite_values():
    assert require_finite_number(123.45, "price") == 123.45
    assert require_finite_number("42.5", "price") == 42.5
    assert require_finite_number(0, "change") == 0.0


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "nan", "inf", "-inf"])
def test_require_finite_number_rejects_non_finite_values(value):
    with pytest.raises(AssertionError, match="not finite"):
        require_finite_number(value, "market value")


@pytest.mark.parametrize("value", [None, "", "not-a-number", object()])
def test_require_finite_number_rejects_non_numeric_values(value):
    with pytest.raises(AssertionError, match="not numeric"):
        require_finite_number(value, "market value")


def test_require_positive_finite_accepts_positive_finite_value():
    assert require_positive_finite(310.34, "price") == 310.34


@pytest.mark.parametrize("value", [0, -1, -0.01, math.nan, math.inf, -math.inf])
def test_require_positive_finite_fails_closed(value):
    with pytest.raises(AssertionError):
        require_positive_finite(value, "price")
