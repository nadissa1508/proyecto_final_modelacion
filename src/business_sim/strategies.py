"""Estrategias de decisión expresadas como cambios en los parámetros."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class StrategyConfig:
    """Magnitudes de las estrategias. Los valores por defecto son los de la cafetería tipo.

    Attributes:
        ad_cost: Gasto mensual en publicidad (Q).
        ad_factor: Multiplicador del coeficiente de innovación p por la publicidad.
        loyalty_churn_cut: Reducción relativa del abandono por el programa de lealtad.
        loyalty_discount: Descuento relativo en el ticket que cuesta la lealtad.
        hires: Empleados adicionales que atienden en mostrador.
        rent_cut: Reducción relativa del alquiler.
        utilities_cut: Reducción relativa de los servicios.
    """

    ad_cost: float = 3_000.0
    ad_factor: float = 4.0
    loyalty_churn_cut: float = 0.25
    loyalty_discount: float = 0.05
    hires: int = 1
    rent_cut: float = 0.20
    utilities_cut: float = 0.10


def describe_strategies(config=None):
    """Devuelve un diccionario {nombre: descripción} de las estrategias con `config`."""
    c = StrategyConfig() if config is None else config
    return {
        "Sin cambios": "Parámetros base.",
        "Publicidad": f"Q{c.ad_cost:,.0f} al mes en publicidad y coeficiente de innovación p multiplicado por {c.ad_factor:g}.",
        "Lealtad": f"Abandono promedio {c.loyalty_churn_cut:.0%} menor a cambio de {c.loyalty_discount:.0%} de descuento en el ticket.",
        "Contratar": f"{c.hires} empleado(s) más que atienden en mostrador.",
        "Recortar fijos": f"Alquiler {c.rent_cut:.0%} menor y servicios {c.utilities_cut:.0%} menores.",
    }


STRATEGIES = describe_strategies()


def apply_strategy(name, p, cp, qp, config=None):
    """Devuelve los parámetros (p, cp, qp) modificados por la estrategia `name`.

    Args:
        name: Clave de `STRATEGIES`.
        p: `BusinessParams` de referencia.
        cp: `CustomerParams` de referencia.
        qp: `QueueParams` de referencia.
        config: `StrategyConfig` con las magnitudes. None usa los valores por defecto.

    Raises:
        KeyError: Si `name` no está en `STRATEGIES`.
    """
    if name not in STRATEGIES:
        raise KeyError(name)
    c = StrategyConfig() if config is None else config
    if name == "Publicidad":
        return (replace(p, other_fixed=p.other_fixed + c.ad_cost),
                replace(cp, innovation=cp.innovation * c.ad_factor), qp)
    if name == "Lealtad":
        return (replace(p, avg_ticket=p.avg_ticket * (1 - c.loyalty_discount)),
                replace(cp, mean_churn=cp.mean_churn * (1 - c.loyalty_churn_cut)), qp)
    if name == "Contratar":
        return replace(p, employees=p.employees + c.hires), cp, replace(qp, servers=qp.servers + c.hires)
    if name == "Recortar fijos":
        return replace(p, rent=p.rent * (1 - c.rent_cut), utilities=p.utilities * (1 - c.utilities_cut)), cp, qp
    return p, cp, qp
