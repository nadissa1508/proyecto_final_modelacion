"""Capa de dinámica de sistemas: caja, inventario y deuda con paso mensual."""

import numpy as np
import pandas as pd


def seasonal_factor(params):
    """Devuelve el multiplicador estacional de cada mes del horizonte.

    Usa un coseno de amplitud `params.seasonality` con pico en diciembre.
    """
    month = (params.start_month - 1 + np.arange(params.horizon)) % 12 + 1
    return 1 + params.seasonality * np.cos(2 * np.pi * (month - 12) / 12)


def demand_curve(params, factor=1.0):
    """Devuelve la demanda esperada de clientes para cada mes del horizonte.

    La demanda crece de `demand_start` hacia `demand_mature` de forma exponencial,
    con la mitad del crecimiento en `ramp_months`, y se multiplica por
    `seasonal_factor`.

    Args:
        params: `BusinessParams` del negocio.
        factor: Multiplicador de la demanda (0.7 equivale a ventas 30 % menores).

    Returns:
        Arreglo de largo `params.horizon` con clientes por mes.
    """
    t = np.arange(params.horizon)
    tau = params.ramp_months / np.log(2)
    base = params.demand_mature - (params.demand_mature - params.demand_start) * np.exp(-t / tau)
    return factor * base * seasonal_factor(params)


def simulate_finance(params, demand, credit_demand=None, bad_demand=None, payment_delay=1):
    """Simula los stocks de caja, inventario, deuda y cuentas por cobrar mes a mes.

    En cada mes se compra inventario hasta cubrir `inventory_cover` meses de la demanda
    del mes anterior, se atiende la demanda que el inventario permite, se descuenta la
    merma y se pagan costos fijos y cuota de la deuda. Las ventas a crédito entran a
    cuentas por cobrar y salen `payment_delay` meses después, como cobro o como
    incobrable. La caja puede quedar negativa para mostrar la profundidad del faltante.

    Args:
        params: `BusinessParams` del negocio.
        demand: Clientes que llegan a comprar en cada mes (largo `params.horizon`).
        credit_demand: Parte de `demand` que compra a crédito. None equivale a ceros.
        bad_demand: Parte de `credit_demand` que no se cobrará. None equivale a ceros.
        payment_delay: Meses entre la venta a crédito y su cobro.

    Returns:
        `DataFrame` indexado por mes (1 a `horizon`) con las columnas
        demand, served, revenue, credit_sales, collected, bad_debt, purchases, spoilage,
        fixed, interest, principal, cash, inventory, debt y receivables. `revenue` son
        las ventas totales del mes y los stocks son valores al cierre del mes.
    """
    demand = np.asarray(demand, dtype=float)
    zeros = np.zeros_like(demand)
    credit_demand = zeros if credit_demand is None else np.asarray(credit_demand, dtype=float)
    bad_demand = zeros if bad_demand is None else np.asarray(bad_demand, dtype=float)
    r = params.annual_rate / 12
    payment = params.loan_payment
    cash, inventory, debt = params.initial_cash, params.initial_inventory, params.loan_amount
    due_good = np.zeros(len(demand) + payment_delay + 1)
    due_bad = np.zeros_like(due_good)
    receivables = 0.0
    forecast = params.demand_start
    rows = []
    for t, d in enumerate(demand):
        purchases = max(0.0, params.inventory_cover * forecast * params.unit_cost - inventory)
        inventory += purchases
        served = min(d, inventory / params.unit_cost)
        inventory -= served * params.unit_cost
        spoilage = params.spoilage_rate * inventory
        inventory -= spoilage

        interest = debt * r
        principal = min(debt, payment - interest) if debt > 0 else 0.0
        debt -= principal

        share = served / d if d > 0 else 0.0
        revenue = served * params.avg_ticket
        credit_sales = credit_demand[t] * share * params.avg_ticket
        bad = bad_demand[t] * share * params.avg_ticket
        due_good[t + payment_delay] += credit_sales - bad
        due_bad[t + payment_delay] += bad
        collected, bad_debt = due_good[t], due_bad[t]
        receivables += credit_sales - collected - bad_debt

        cash += revenue - credit_sales + collected - purchases - params.fixed_costs - interest - principal
        rows.append({
            "demand": d, "served": served, "revenue": revenue, "credit_sales": credit_sales,
            "collected": collected, "bad_debt": bad_debt, "purchases": purchases,
            "spoilage": spoilage, "fixed": params.fixed_costs, "interest": interest,
            "principal": principal, "cash": cash, "inventory": inventory, "debt": debt,
            "receivables": receivables,
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
