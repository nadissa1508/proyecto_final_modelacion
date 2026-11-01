"""Capa de servicio: responde las preguntas del simulador con resultados serializables a JSON.

Cada función recibe un `BusinessInput` o un diccionario con sus campos y devuelve un
diccionario con números, listas y textos, listo para enviarse a un frontend.
"""

import math
import os
import time
from dataclasses import replace
from functools import lru_cache

import numpy as np

from .customers import simulate_customers
from .finance import demand_curve, months_survived, seasonal_factor, simulate_finance
from .inputs import BusinessInput
from .montecarlo import run_montecarlo
from .params import CreditParams
from .queue_des import loss_table
from .strategies import STRATEGIES, apply_strategy, describe_strategies

WORKERS = os.cpu_count() or 1
"""Procesos que usa Monte Carlo en las funciones del servicio."""

SENSITIVITY_FIELDS = {
    "initial_cash": ("p", "Caja inicial"),
    "avg_ticket": ("p", "Ticket promedio"),
    "unit_cost": ("p", "Costo de insumos"),
    "rent": ("p", "Alquiler"),
    "salary": ("p", "Salario"),
    "imitation": ("cp", "Boca a boca"),
    "mean_churn": ("cp", "Abandono"),
    "mean_visits": ("cp", "Visitas por cliente"),
}


def _as_input(data):
    """Convierte un diccionario en `BusinessInput` validado o valida el objeto recibido."""
    if isinstance(data, BusinessInput):
        data.validate()
        return data
    return BusinessInput.from_dict(data or {})


def _clean(obj):
    """Convierte tipos de NumPy y valores no finitos en tipos nativos serializables."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [_clean(v) for v in obj.tolist()]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj) if math.isfinite(obj) else None
    return obj


@lru_cache(maxsize=16)
def _cached_table(qp, grid, servers, seed):
    return loss_table(qp, list(grid), list(servers), days=40, seed=seed)


def _context(inp, seed):
    """Devuelve (p, cp, qp, crp, tabla) para `inp`, con la tabla de la cola en caché."""
    p, cp, qp, crp = inp.to_params()
    peak = p.demand_mature * (1 + p.seasonality) * 1.6 / qp.days_per_month
    vmax = max(50, int(math.ceil(peak / 10) * 10))
    grid = tuple(int(round(v)) for v in np.linspace(0, vmax, 21))
    s, h = qp.servers, inp.strategies.hires
    servers = tuple(sorted({max(1, s - 1), s, s + 1, s + h, s + 2}))
    return p, cp, qp, crp, _cached_table(qp, grid, servers, seed)


def _range(r):
    """Devuelve los escenarios peor (P10), probable (P50) y mejor (P90) de un resumen Monte Carlo."""
    out = {}
    for name, q in [("worst", 0.1), ("likely", 0.5), ("best", 0.9)]:
        out[name] = {
            "months_survived": r["months"].quantile(q),
            "min_cash": r["min_cash"].quantile(q),
            "final_cash": r["final_cash"].quantile(q),
        }
    return out


def summary(data):
    """Resume el negocio sin incertidumbre y muestra la calibración de clientes.

    Returns:
        Diccionario con costos mensuales, margen, equilibrio, visitas esperadas, caja
        determinista, meses que aguanta sin incertidumbre y la población calibrada con
        su error porcentual medio frente a las visitas esperadas (5 réplicas de la ABM).
    """
    inp = _as_input(data)
    p, cp, qp, crp = inp.to_params()
    demand = demand_curve(p)
    fin = simulate_finance(p, demand)
    visits = np.array([simulate_customers(cp, seasonal_factor(p), rng=i)["visits"] for i in range(5)]).mean(axis=0)
    return _clean({
        "name": inp.name,
        "fixed_costs": p.fixed_costs,
        "loan_payment": p.loan_payment,
        "margin_per_visit": p.margin,
        "breakeven_visits": p.breakeven_customers,
        "expected_visits": demand,
        "deterministic_cash": fin["cash"].to_numpy(),
        "deterministic_months_survived": months_survived(fin),
        "calibration": {
            "population": cp.population,
            "initial_customers": cp.initial_customers,
            "imitation": cp.imitation,
            "innovation": cp.innovation,
            "mean_churn": cp.mean_churn,
            "abm_visits": visits,
            "mean_abs_pct_error": float(np.mean(np.abs(visits - demand) / demand)),
        },
    })


def survival(data, n=500, seed=0, sales_change=0.0):
    """Estima el riesgo de quedarse sin caja con Monte Carlo.

    Args:
        data: `BusinessInput` o diccionario.
        n: Número de escenarios.
        seed: Semilla base.
        sales_change: Cambio relativo de las visitas (-0.3 equivale a 30 % menos).

    Returns:
        Diccionario con probability_out_of_cash, probability_survive, range (peor,
        probable y mejor), cash_fan (P10, P50 y P90 de la caja por mes),
        months_histogram, mean_queue_loss y bad_debt_median.
    """
    inp = _as_input(data)
    p, cp, qp, crp, table = _context(inp, seed)
    r, cash = run_montecarlo(n, p, cp, qp, table, seed=seed, level=1 + sales_change, crp=crp, workers=WORKERS)
    p10, p50, p90 = np.quantile(cash, [0.1, 0.5, 0.9], axis=0)
    counts = np.bincount(r["months"].to_numpy(), minlength=p.horizon + 1)
    return _clean({
        "sales_change": sales_change,
        "n": n,
        "probability_out_of_cash": 1 - r["survived"].mean(),
        "probability_survive": r["survived"].mean(),
        "range": _range(r),
        "cash_fan": {"month": np.arange(1, p.horizon + 1), "p10": p10, "p50": p50, "p90": p90},
        "months_histogram": {"months": np.arange(p.horizon + 1), "count": counts},
        "mean_queue_loss": r["mean_loss"].mean(),
        "bad_debt_median": r["bad_debt"].median(),
    })


def sales_drop(data, drop=0.3, n=500, seed=0):
    """Compara la supervivencia con las ventas esperadas y con ventas `drop` menores.

    Returns:
        Diccionario con drop, expected y reduced (salidas de `survival`).
    """
    inp = _as_input(data)
    return {
        "drop": drop,
        "expected": survival(inp, n, seed),
        "reduced": survival(inp, n, seed, sales_change=-drop),
    }


def retention(data, target_risk=0.10, retentions=(0.80, 0.84, 0.88, 0.90, 0.92, 0.94, 0.96, 0.98), n=300, seed=0):
    """Estima qué retención mensual de clientes se necesita para no quedarse sin caja.

    La retención se aplica sobre la población ya calibrada, por lo que responde qué
    pasaría si los clientes se quedaran más o menos de lo esperado.

    Args:
        data: `BusinessInput` o diccionario.
        target_risk: Probabilidad máxima aceptada de quedarse sin caja.
        retentions: Retenciones mensuales a evaluar.
        n: Escenarios por retención.
        seed: Semilla base.

    Returns:
        Diccionario con expected_retention, target_risk, rows (una por retención) y
        min_retention (la menor que cumple el riesgo, o None).
    """
    inp = _as_input(data)
    p, cp, qp, crp, table = _context(inp, seed)
    rows = []
    for ret in sorted(retentions):
        r, _ = run_montecarlo(n, p, replace(cp, mean_churn=1 - ret), qp, table, seed=seed, crp=crp, workers=WORKERS)
        active = r["active_end"].median()
        rows.append({
            "retention": ret,
            "probability_survive": r["survived"].mean(),
            "median_months": r["months"].median(),
            "median_active_end": active,
            "retained_customers_per_month": active * ret,
        })
    ok = [row["retention"] for row in rows if 1 - row["probability_survive"] <= target_risk]
    return _clean({
        "expected_retention": inp.monthly_retention,
        "target_risk": target_risk,
        "rows": rows,
        "min_retention": min(ok) if ok else None,
    })


def strategies(data, n=300, seed=0, sales_changes=(0.0, -0.3)):
    """Compara las estrategias en uno o más escenarios de ventas y recomienda una por escenario.

    La recomendación es la estrategia con mayor probabilidad de llegar al final del
    horizonte y, en empate, la de mayor caja final mediana.

    Returns:
        Diccionario con descriptions y scenarios. Cada escenario tiene sales_change,
        rows (una por estrategia) y recommendation.
    """
    inp = _as_input(data)
    p, cp, qp, crp, table = _context(inp, seed)
    scenarios = []
    for change in sales_changes:
        rows = []
        for name in STRATEGIES:
            ps, cs, qs = apply_strategy(name, p, cp, qp, inp.strategies)
            r, _ = run_montecarlo(n, ps, cs, qs, table, seed=seed, level=1 + change, crp=crp, workers=WORKERS)
            rows.append({
                "strategy": name,
                "probability_survive": r["survived"].mean(),
                "median_months": r["months"].median(),
                "final_cash_p10": r["final_cash"].quantile(0.1),
                "final_cash_p50": r["final_cash"].median(),
                "final_cash_p90": r["final_cash"].quantile(0.9),
                "mean_queue_loss": r["mean_loss"].mean(),
            })
        best = max(rows, key=lambda row: (row["probability_survive"], row["final_cash_p50"]))
        scenarios.append({"sales_change": change, "rows": rows, "recommendation": best["strategy"]})
    return _clean({"descriptions": describe_strategies(inp.strategies), "scenarios": scenarios})


def sensitivity(data, n=300, seed=0, delta=0.2):
    """Mide cómo cambia la probabilidad de llegar al final del horizonte con cada parámetro.

    Cada parámetro se multiplica por 1 - `delta` y 1 + `delta`, uno a la vez.

    Returns:
        Diccionario con base_probability, delta y rows ordenadas de mayor a menor rango.
    """
    inp = _as_input(data)
    p, cp, qp, crp, table = _context(inp, seed)
    base = run_montecarlo(n, p, cp, qp, table, seed=seed, crp=crp, workers=WORKERS)[0]["survived"].mean()
    rows = []
    for name, (group, label) in SENSITIVITY_FIELDS.items():
        probs = []
        for f in (1 - delta, 1 + delta):
            ps, cs = p, cp
            if group == "p":
                ps = replace(p, **{name: getattr(p, name) * f})
                if ps.unit_cost >= ps.avg_ticket:
                    probs.append(0.0)
                    continue
            else:
                cs = replace(cp, **{name: min(getattr(cp, name) * f, 0.99) if name == "mean_churn" else getattr(cp, name) * f})
            probs.append(run_montecarlo(n, ps, cs, qp, table, seed=seed, crp=crp, workers=WORKERS)[0]["survived"].mean())
        rows.append({"parameter": name, "label": label, "low": probs[0], "high": probs[1], "range": abs(probs[1] - probs[0])})
    rows.sort(key=lambda row: row["range"], reverse=True)
    return _clean({"base_probability": base, "delta": delta, "rows": rows})


def credit(data, n=300, seed=0, share=0.2, defaults=(0.0, 0.02, 0.05, 0.10, 0.15, 0.20), delays=(1, 2, 3), max_drop=0.05):
    """Evalúa la venta a crédito y la morosidad.

    Si el negocio no vende a crédito, se evalúa la pregunta "¿qué pasaría si vendiera a
    crédito a una fracción `share` de sus clientes?" con su plazo y mora declarados.

    Args:
        data: `BusinessInput` o diccionario.
        n: Escenarios por punto.
        seed: Semilla base.
        share: Fracción a crédito para el caso hipotético.
        defaults: Moras mensuales a evaluar.
        delays: Plazos de cobro a evaluar (meses).
        max_drop: Caída máxima aceptada en la probabilidad de llegar al final frente a
            vender solo al contado.

    Returns:
        Diccionario con what_if, credit_share, cash_only, with_credit, default_curve,
        delay_curve, max_drop y max_tolerable_default (o None).
    """
    inp = _as_input(data)
    p, cp, qp, crp, table = _context(inp, seed)
    what_if = crp is None
    if what_if:
        crp = CreditParams(credit_share=share, payment_delay=inp.payment_delay,
                           mean_default=inp.monthly_default, default_churn=inp.default_churn)

    def run(c):
        return run_montecarlo(n, p, cp, qp, table, seed=seed, crp=c, workers=WORKERS)[0]

    cash_only = run(None)
    with_credit = run(crp)
    base_prob = cash_only["survived"].mean()
    default_curve = [{"monthly_default": d, "probability_survive": run(replace(crp, mean_default=d))["survived"].mean()}
                     for d in defaults]
    delay_curve = [{"payment_delay": d, "probability_survive": run(replace(crp, payment_delay=d))["survived"].mean()}
                   for d in delays]
    ok = [row["monthly_default"] for row in default_curve if row["probability_survive"] >= base_prob - max_drop]
    return _clean({
        "what_if": what_if,
        "credit_share": crp.credit_share,
        "cash_only": {"probability_survive": base_prob, "final_cash_p50": cash_only["final_cash"].median()},
        "with_credit": {
            "probability_survive": with_credit["survived"].mean(),
            "final_cash_p50": with_credit["final_cash"].median(),
            "bad_debt_p50": with_credit["bad_debt"].median(),
            "bad_debt_p90": with_credit["bad_debt"].quantile(0.9),
        },
        "default_curve": default_curve,
        "delay_curve": delay_curve,
        "max_drop": max_drop,
        "max_tolerable_default": max(ok) if ok else None,
    })


def full_report(data, n=500, n_grid=300, seed=0, drop=0.3):
    """Ejecuta todas las preguntas y devuelve un solo reporte.

    Args:
        data: `BusinessInput` o diccionario.
        n: Escenarios de las preguntas de supervivencia.
        n_grid: Escenarios por punto en retención, estrategias, sensibilidad y crédito.
        seed: Semilla base.
        drop: Caída de ventas a evaluar.

    Returns:
        Diccionario con input, summary, survival, sales_drop, retention, strategies,
        sensitivity, credit y elapsed_seconds.
    """
    start = time.perf_counter()
    inp = _as_input(data)
    expected = survival(inp, n, seed)
    report = {
        "input": inp.to_dict(),
        "summary": summary(inp),
        "survival": expected,
        "sales_drop": {"drop": drop, "expected": expected, "reduced": survival(inp, n, seed, sales_change=-drop)},
        "retention": retention(inp, n=n_grid, seed=seed),
        "strategies": strategies(inp, n=n_grid, seed=seed, sales_changes=(0.0, -drop)),
        "sensitivity": sensitivity(inp, n=n_grid, seed=seed),
        "credit": credit(inp, n=n_grid, seed=seed),
    }
    report["elapsed_seconds"] = time.perf_counter() - start
    return _clean(report)
