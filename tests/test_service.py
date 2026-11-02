"""Pruebas de la capa de servicio con pocos escenarios."""

import json

import pytest

from business_sim import service

STORE = {"name": "Tienda", "sales_start": 400, "sales_mature": 800, "employees": 2, "servers": 1,
         "hourly_profile": None, "opening_hour": 8, "closing_hour": 20, "credit_share": 0.2}


def test_summary():
    r = service.summary({})
    json.dumps(r)
    assert round(r["breakeven_visits"]) == 1021
    assert r["calibration"]["mean_abs_pct_error"] < 0.1


@pytest.mark.parametrize("func, kwargs, keys", [
    (service.survival, {"n": 8}, {"probability_survive", "range", "cash_fan", "months_histogram"}),
    (service.sales_drop, {"n": 8}, {"expected", "reduced"}),
    (service.retention, {"n": 8, "retentions": (0.9, 0.95)}, {"rows", "min_retention"}),
    (service.strategies, {"n": 8, "sales_changes": (0.0,)}, {"descriptions", "scenarios"}),
    (service.sensitivity, {"n": 8}, {"base_probability", "rows"}),
    (service.credit, {"n": 8, "defaults": (0.0, 0.1), "delays": (1,)}, {"cash_only", "with_credit", "default_curve"}),
])
def test_reports_are_json(func, kwargs, keys):
    r = func(STORE, **kwargs)
    json.dumps(r)
    assert keys <= set(r)


def test_strategy_recommendation_is_a_strategy():
    r = service.strategies(STORE, n=8, sales_changes=(0.0,))
    assert r["scenarios"][0]["recommendation"] in r["descriptions"]


def test_invalid_input_raises():
    with pytest.raises(ValueError):
        service.summary({"unit_cost": 100})
