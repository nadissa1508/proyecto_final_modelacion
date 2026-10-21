"""Capa de dinámica de sistemas: caja, inventario y deuda con paso mensual."""

import numpy as np
import pandas as pd


def demand_curve(params, factor=1.0):
    """Devuelve la demanda esperada de clientes para cada mes del horizonte.

    La demanda crece de `demand_start` hacia `demand_mature` de forma exponencial,
    con la mitad del crecimiento en `ramp_months`, y se multiplica por una
    estacionalidad coseno con pico en diciembre.

    Args:
        params: `BusinessParams` del negocio.
        factor: Multiplicador de la demanda (0.7 equivale a ventas 30 % menores).

    Returns:
        Arreglo de largo `params.horizon` con clientes por mes.
    """
    t = np.arange(params.horizon)
    tau = params.ramp_months / np.log(2)
    base = params.demand_mature - (params.demand_mature - params.demand_start) * np.exp(-t / tau)
    month = (params.start_month - 1 + t) % 12 + 1
    season = 1 + params.seasonality * np.cos(2 * np.pi * (month - 12) / 12)
    return factor * base * season


def simulate_finance(params, demand):
    """Simula los stocks de caja, inventario y deuda mes a mes.

    En cada mes se compra inventario hasta cubrir `inventory_cover` meses de la demanda
    del mes anterior, se atiende la demanda que el inventario permite, se descuenta la
    merma y se pagan costos fijos y cuota de la deuda. La caja puede quedar negativa
    para mostrar la profundidad del faltante.

    Args:
        params: `BusinessParams` del negocio.
        demand: Clientes que llegan a comprar en cada mes (largo `params.horizon`).

    Returns:
        `DataFrame` indexado por mes (1 a `horizon`) con las columnas
        demand, served, revenue, purchases, spoilage, fixed, interest, principal,
        cash, inventory y debt. Los stocks son valores al cierre del mes.
    """
    demand = np.asarray(demand, dtype=float)
    r = params.annual_rate / 12
    payment = params.loan_payment
    cash, inventory, debt = params.initial_cash, params.initial_inventory, params.loan_amount
    forecast = params.demand_start
    rows = []
    for d in demand:
        purchases = max(0.0, params.inventory_cover * forecast * params.unit_cost - inventory)
        inventory += purchases
        served = min(d, inventory / params.unit_cost)
        inventory -= served * params.unit_cost
        spoilage = params.spoilage_rate * inventory
        inventory -= spoilage

        interest = debt * r
        principal = min(debt, payment - interest) if debt > 0 else 0.0
        debt -= principal

        revenue = served * params.avg_ticket
        cash += revenue - purchases - params.fixed_costs - interest - principal
        rows.append({
            "demand": d, "served": served, "revenue": revenue, "purchases": purchases,
            "spoilage": spoilage, "fixed": params.fixed_costs, "interest": interest,
            "principal": principal, "cash": cash, "inventory": inventory, "debt": debt,
        })
        forecast = d
    df = pd.DataFrame(rows)
    df.index = pd.RangeIndex(1, len(df) + 1, name="month")
    return df


def months_survived(df):
    """Devuelve los meses completos con caja no negativa antes del primer faltante.

    Si la caja nunca es negativa, devuelve el largo del horizonte.
    """
    negative = np.flatnonzero(df["cash"].to_numpy() < 0)
    return int(negative[0]) if negative.size else len(df)
