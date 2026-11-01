"""Calibración de la población de agentes a partir de las ventas esperadas del dueño."""

from dataclasses import replace

import numpy as np
from scipy.optimize import minimize

from .params import CustomerParams


def expected_visits(start, mature, ramp_months, horizon):
    """Devuelve la curva de visitas esperadas sin estacionalidad (misma forma que `demand_curve`)."""
    t = np.arange(horizon)
    return mature - (mature - start) * np.exp(-t * np.log(2) / ramp_months)


def mean_field_visits(population, initial, innovation, imitation, churn, mean_visits, horizon):
    """Aproxima las visitas mensuales de la población con una versión agregada del modelo.

    Repite el orden de `CustomerPopulation.step` con la fracción activa en lugar de la
    fracción de contactos activos y con el abandono promedio.

    Returns:
        Arreglo de largo `horizon` con visitas esperadas por mes.
    """
    a = float(initial)
    out = np.empty(horizon)
    for t in range(horizon):
        a += (population - a) * (1 - np.exp(-(innovation + imitation * a / population)))
        out[t] = a * mean_visits
        a *= 1 - churn
    return out


def calibrate_customers(start, mature, ramp_months, mean_visits, churn, horizon=24, base=None):
    """Ajusta población, boca a boca y clientes iniciales para reproducir las ventas esperadas.

    Se minimiza el error cuadrático relativo entre `mean_field_visits` y
    `expected_visits` sobre el logaritmo de la población y de `imitation`. Los clientes
    iniciales se obtienen para que el primer mes coincida con `start`.

    Args:
        start: Visitas esperadas en el primer mes.
        mature: Visitas esperadas por mes cuando el negocio madura.
        ramp_months: Mes en que se alcanza la mitad del crecimiento.
        mean_visits: Visitas promedio por mes de un cliente activo.
        churn: Probabilidad de abandono mensual promedio.
        horizon: Meses del ajuste.
        base: `CustomerParams` del que se copian los demás campos. None usa los por defecto.

    Returns:
        `CustomerParams` calibrado.
    """
    base = CustomerParams() if base is None else base
    target = expected_visits(start, mature, ramp_months, horizon)
    p = base.innovation

    def initial_for(n, q):
        lo, hi = 0.0, start / mean_visits
        for _ in range(50):
            mid = (lo + hi) / 2
            a = mid + (n - mid) * (1 - np.exp(-(p + q * mid / n)))
            lo, hi = (mid, hi) if a * mean_visits < start else (lo, mid)
        return (lo + hi) / 2

    def error(x):
        n, q = np.exp(x)
        if n < start / mean_visits:
            return 1e6
        v = mean_field_visits(n, initial_for(n, q), p, q, churn, mean_visits, horizon)
        return float(np.mean(((v - target) / target) ** 2))

    x0 = np.log([1.5 * mature / mean_visits, 0.25])
    res = minimize(error, x0, method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-10, "maxiter": 2000})
    n, q = np.exp(res.x)
    return replace(
        base, population=int(round(n)), imitation=float(q),
        initial_customers=int(round(initial_for(n, q))), mean_visits=mean_visits, mean_churn=churn,
    )
