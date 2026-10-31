"""Monte Carlo sobre el modelo integrado para estimar el riesgo de quedarse sin caja."""

from dataclasses import replace

import numpy as np
import pandas as pd

from .finance import months_survived
from .model import simulate_business


def sample_scenario(p, cp, rng, crp=None):
    """Sortea un escenario incierto alrededor de los parámetros dados.

    Se sortean el nivel de mercado (lognormal de media 1 y desviación 0.15), los
    multiplicadores del boca a boca y del abandono (uniformes entre 0.75 y 1.25), el
    multiplicador del costo unitario (triangular 0.95, 1, 1.15) y el ticket promedio
    (normal con desviación de Q2). Si hay venta a crédito, también se sortea el
    multiplicador de la mora (uniforme entre 0.75 y 1.25).

    Args:
        p: `BusinessParams` de referencia.
        cp: `CustomerParams` de referencia.
        rng: `numpy.random.Generator`.
        crp: `CreditParams` opcional de referencia.

    Returns:
        Tupla (p, cp, level, crp) del escenario.
    """
    level = rng.lognormal(-0.15**2 / 2, 0.15)
    cp_s = replace(cp, imitation=cp.imitation * rng.uniform(0.75, 1.25),
                   mean_churn=cp.mean_churn * rng.uniform(0.75, 1.25))
    p_s = replace(p, unit_cost=p.unit_cost * rng.triangular(0.95, 1.0, 1.15),
                  avg_ticket=rng.normal(p.avg_ticket, 2.0))
    if crp is not None and crp.credit_share > 0:
        crp = replace(crp, mean_default=min(crp.mean_default * rng.uniform(0.75, 1.25), 0.99))
    return p_s, cp_s, level, crp


def run_montecarlo(n, p, cp, qp, table, seed=0, level=1.0, noise=0.05, crp=None):
    """Corre `n` escenarios del modelo integrado.

    El escenario i usa la semilla (seed, i), por lo que dos llamadas con la misma
    semilla comparten los sorteos (números aleatorios comunes).

    Args:
        n: Número de escenarios.
        p, cp, qp: Parámetros del negocio, la población y la atención.
        table: Tabla de `loss_table`.
        seed: Semilla base.
        level: Multiplicador adicional del nivel de visitas.
        noise: Desviación del choque lognormal mensual de las visitas.
        crp: `CreditParams` opcional.

    Returns:
        Tupla (summary, cash). `summary` es un `DataFrame` con una fila por escenario y
        las columnas months, survived, min_cash, final_cash, active_end, mean_loss,
        churn y bad_debt (incobrables acumulados). `cash` es un arreglo (n, horizon) con la caja al cierre de cada mes.
    """
    rows, cash = [], []
    for i in range(n):
        rng = np.random.default_rng([seed, i])
        p_s, cp_s, lev, crp_s = sample_scenario(p, cp, rng, crp)
        df = simulate_business(p_s, cp_s, qp, table, rng, level=level * lev, noise=noise, crp=crp_s)
        m = months_survived(df)
        rows.append({
            "months": m, "survived": m == p.horizon, "min_cash": df["cash"].min(),
            "final_cash": df["cash"].iloc[-1], "active_end": df["active"].iloc[-1],
            "mean_loss": df["loss"].mean(), "churn": cp_s.mean_churn,
            "bad_debt": df["bad_debt"].sum(),
        })
        cash.append(df["cash"].to_numpy())
    return pd.DataFrame(rows), np.array(cash)
