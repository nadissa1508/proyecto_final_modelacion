"""Pruebas de la caja, el crédito y Monte Carlo."""

import numpy as np

from business_sim.finance import demand_curve, months_survived, simulate_finance
from business_sim.model import simulate_business
from business_sim.montecarlo import run_montecarlo
from business_sim.params import CreditParams


def test_finance_without_credit_ignores_credit_columns(params):
    p = params[0]
    d = demand_curve(p)
    a = simulate_finance(p, d)
    b = simulate_finance(p, d, np.zeros_like(d), np.zeros_like(d))
    assert a.equals(b)
    assert (a["receivables"] == 0).all()


def test_months_survived(params):
    p = params[0]
    assert months_survived(simulate_finance(p, demand_curve(p))) == p.horizon
    assert months_survived(simulate_finance(p, demand_curve(p, 0.7))) == 5


def test_credit_conservation(params, table):
    p, cp, qp = params
    df = simulate_business(p, cp, qp, table, rng=1, crp=CreditParams(credit_share=0.3, payment_delay=2))
    total = df["collected"].sum() + df["bad_debt"].sum() + df["receivables"].iloc[-1]
    assert np.isclose(df["credit_sales"].sum(), total)
    assert df["bad_debt"].sum() > 0


def test_zero_credit_share_equals_cash_only(params, table):
    p, cp, qp = params
    a = simulate_business(p, cp, qp, table, rng=1)
    b = simulate_business(p, cp, qp, table, rng=1, crp=CreditParams(credit_share=0.0))
    assert a.equals(b)


def test_parallel_equals_serial(params, table):
    p, cp, qp = params
    a, ca = run_montecarlo(12, p, cp, qp, table, seed=3)
    b, cb = run_montecarlo(12, p, cp, qp, table, seed=3, workers=2)
    assert a.equals(b) and np.array_equal(ca, cb)
