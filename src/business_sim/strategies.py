"""Estrategias de decisión expresadas como cambios en los parámetros."""

from dataclasses import replace

STRATEGIES = {
    "Sin cambios": "Parámetros base.",
    "Publicidad": "Q3 000 al mes en publicidad y coeficiente de innovación p de 0.005 a 0.02.",
    "Lealtad": "Abandono promedio 25 % menor a cambio de 5 % de descuento en el ticket.",
    "Contratar": "Un empleado más que atiende en mostrador (un servidor adicional).",
    "Recortar fijos": "Alquiler 20 % menor y servicios 10 % menores.",
}


def apply_strategy(name, p, cp, qp):
    """Devuelve los parámetros (p, cp, qp) modificados por la estrategia `name`.

    Args:
        name: Clave de `STRATEGIES`.
        p: `BusinessParams` de referencia.
        cp: `CustomerParams` de referencia.
        qp: `QueueParams` de referencia.

    Raises:
        KeyError: Si `name` no está en `STRATEGIES`.
    """
    if name not in STRATEGIES:
        raise KeyError(name)
    if name == "Publicidad":
        return replace(p, other_fixed=p.other_fixed + 3_000), replace(cp, innovation=0.02), qp
    if name == "Lealtad":
        return replace(p, avg_ticket=p.avg_ticket * 0.95), replace(cp, mean_churn=cp.mean_churn * 0.75), qp
    if name == "Contratar":
        return replace(p, employees=p.employees + 1), cp, replace(qp, servers=qp.servers + 1)
    if name == "Recortar fijos":
        return replace(p, rent=p.rent * 0.8, utilities=p.utilities * 0.9), cp, qp
    return p, cp, qp
