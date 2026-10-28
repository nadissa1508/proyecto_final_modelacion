"""Modelo integrado: agentes, cola y dinámica de sistemas acoplados mes a mes."""

import numpy as np
import pandas as pd

from .customers import CustomerPopulation
from .finance import seasonal_factor, simulate_finance
from .queue_des import loss_fraction


def simulate_business(p, cp, qp, table, rng=None, level=1.0, noise=0.0):
    """Simula un escenario completo del negocio.

    Cada mes la población de agentes genera visitas, la tabla de la cola estima qué
    fracción se pierde con `qp.servers` servidores y esa fracción aumenta el abandono
    del mes siguiente. Las visitas atendidas son la demanda de `simulate_finance`.

    Args:
        p: `BusinessParams` del negocio.
        cp: `CustomerParams` de la población.
        qp: `QueueParams` de la atención.
        table: Tabla de `loss_table` con una columna para `qp.servers`.
        rng: `numpy.random.Generator` o semilla.
        level: Multiplicador del nivel de visitas (0.7 equivale a ventas 30 % menores).
        noise: Desviación estándar del choque lognormal mensual de las visitas.

    Returns:
        `DataFrame` indexado por mes con las columnas de la población (active, new,
        visits, churned), loss, queue_served y las columnas de `simulate_finance`.
    """
    rng = np.random.default_rng(rng)
    pop = CustomerPopulation(cp, rng)
    shocks = rng.lognormal(-noise**2 / 2, noise, p.horizon) if noise > 0 else np.ones(p.horizon)
    loss = 0.0
    rows = []
    for s in seasonal_factor(p) * level * shocks:
        counts = pop.step(s, unserved_share=loss)
        loss = float(loss_fraction(table, counts["visits"] / qp.days_per_month, qp.servers))
        rows.append({**counts, "loss": loss, "queue_served": counts["visits"] * (1 - loss)})
    customers = pd.DataFrame(rows)
    customers.index = pd.RangeIndex(1, len(customers) + 1, name="month")
    return customers.join(simulate_finance(p, customers["queue_served"]))
