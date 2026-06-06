import math

import pytest

from backend.etl.etl_nhanes import calculate_egfr


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"Creatinine": 1.0, "Age": 50, "Gender": 1}, 91.6914786098333),
        ({"Creatinine": 0.8, "Age": 50, "Gender": 2}, 89.70737342385397),
    ],
)
def test_calculate_egfr_uses_2021_ckd_epi_creatinine_formula(row, expected):
    assert calculate_egfr(row) == pytest.approx(expected, abs=1e-6)


def test_calculate_egfr_returns_nan_when_required_fields_missing():
    assert math.isnan(calculate_egfr({"Age": 50, "Gender": 1}))
