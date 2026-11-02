"""Pruebas de la calibración de clientes."""

import numpy as np
import pytest

from business_sim.calibration import calibrate_customers, expected_visits
from business_sim.customers import simulate_customers


@pytest.mark.parametrize("start, mature, ramp, visits, churn", [
    (700, 1600, 6, 2.0, 0.08),
    (300, 600, 4, 4.0, 0.05),
    (1500, 1200, 3, 3.0, 0.06),
])
def test_abm_reproduces_expected_visits(start, mature, ramp, visits, churn):
    cp = calibrate_customers(start, mature, ramp, visits, churn)
    target = expected_visits(start, mature, ramp, 24)
    sim = np.array([simulate_customers(cp, np.ones(24), rng=i)["visits"] for i in range(5)]).mean(axis=0)
    assert np.mean(np.abs(sim - target) / target) < 0.05
