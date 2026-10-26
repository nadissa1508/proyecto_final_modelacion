"""Capa de eventos discretos: cola de atención en mostrador simulada con SimPy."""

import math

import numpy as np
import pandas as pd
import simpy


def simulate_queue(hourly_rates, servers, service_mean, patience_mean, max_queue, rng):
    """Simula una cola de c servidores con llegadas Poisson por tramos de una hora.

    Quien llega y encuentra `max_queue` o más clientes en cola se va sin entrar. Quien
    entra a la cola se va si su paciencia (exponencial) se agota antes de ser atendido.
    Las llegadas ocurren solo dentro del horario y los clientes en sistema al cierre
    terminan su atención.

    Args:
        hourly_rates: Llegadas esperadas en cada hora (secuencia, una por hora).
        servers: Número de servidores.
        service_mean: Tiempo promedio de servicio (minutos, exponencial).
        patience_mean: Paciencia promedio (minutos). `math.inf` desactiva el abandono.
        max_queue: Largo de cola que provoca desistir al llegar. `math.inf` lo desactiva.
        rng: `numpy.random.Generator`.

    Returns:
        Diccionario con arrivals, served, balked, reneged, lost_share y mean_wait
        (espera promedio en cola de los atendidos, en minutos).
    """
    env = simpy.Environment()
    desk = simpy.Resource(env, capacity=servers)
    stats = {"served": 0, "balked": 0, "reneged": 0, "wait": 0.0}

    times = []
    for h, rate in enumerate(hourly_rates):
        n = rng.poisson(rate)
        times.extend(60 * h + 60 * rng.random(n))
    times.sort()

    def customer(arrival):
        if len(desk.queue) >= max_queue:
            stats["balked"] += 1
            return
        patience = rng.exponential(patience_mean) if math.isfinite(patience_mean) else math.inf
        with desk.request() as req:
            result = yield req | env.timeout(patience) if math.isfinite(patience) else req
            if math.isfinite(patience) and req not in result:
                stats["reneged"] += 1
                return
            stats["wait"] += env.now - arrival
            yield env.timeout(rng.exponential(service_mean))
            stats["served"] += 1

    def source():
        for t in times:
            yield env.timeout(t - env.now)
            env.process(customer(t))

    env.process(source())
    env.run()
    arrivals = len(times)
    lost = stats["balked"] + stats["reneged"]
    return {
        "arrivals": arrivals,
        "served": stats["served"],
        "balked": stats["balked"],
        "reneged": stats["reneged"],
        "lost_share": lost / arrivals if arrivals else 0.0,
        "mean_wait": stats["wait"] / stats["served"] if stats["served"] else 0.0,
    }


def hourly_rates(daily_visits, qparams):
    """Reparte las visitas de un día entre las horas según `qparams.hourly_profile`."""
    w = np.asarray(qparams.hourly_profile, dtype=float)
    return daily_visits * w / w.sum()


def simulate_day(daily_visits, qparams, rng, servers=None):
    """Simula un día de atención con el perfil horario de `qparams`.

    Args:
        daily_visits: Visitas esperadas en el día.
        qparams: `QueueParams` de la atención.
        rng: `numpy.random.Generator`.
        servers: Servidores del día. Si es None se usa `qparams.servers`.

    Returns:
        Diccionario de `simulate_queue`.
    """
    return simulate_queue(
        hourly_rates(daily_visits, qparams),
        qparams.servers if servers is None else servers,
        qparams.service_mean, qparams.patience_mean, qparams.max_queue, rng,
    )


def loss_table(qparams, visits_grid, servers_grid, days=30, seed=0):
    """Estima la fracción de visitas perdidas para cada combinación de visitas y servidores.

    La fracción es el total de clientes perdidos entre el total de llegadas de `days`
    días simulados.

    Args:
        qparams: `QueueParams` de la atención.
        visits_grid: Visitas diarias a evaluar (creciente).
        servers_grid: Números de servidores a evaluar.
        days: Días simulados por combinación.
        seed: Semilla base.

    Returns:
        `DataFrame` con índice visitas diarias y una columna por número de servidores.
    """
    rng = np.random.default_rng(seed)
    table = {}
    for c in servers_grid:
        col = []
        for v in visits_grid:
            runs = [simulate_day(v, qparams, rng, servers=c) for _ in range(days)]
            arrivals = sum(r["arrivals"] for r in runs)
            lost = sum(r["balked"] + r["reneged"] for r in runs)
            col.append(lost / arrivals if arrivals else 0.0)
        table[c] = col
    return pd.DataFrame(table, index=pd.Index(visits_grid, name="daily_visits"))


def loss_fraction(table, daily_visits, servers):
    """Interpola linealmente la fracción perdida de `loss_table` para las visitas dadas.

    Fuera de la malla se usa el valor del extremo más cercano.
    """
    return np.interp(daily_visits, table.index.to_numpy(dtype=float), table[servers].to_numpy())


def mmc_wait(lam, mu, c):
    """Devuelve la espera promedio en cola Wq de la fila M/M/c (fórmula de Erlang C).

    Args:
        lam: Tasa de llegadas.
        mu: Tasa de servicio por servidor.
        c: Número de servidores. Requiere lam < c mu.
    """
    a = lam / mu
    b = 1.0
    for k in range(1, c + 1):
        b = a * b / (k + a * b)
    rho = a / c
    erlang_c = b / (1 - rho * (1 - b))
    return erlang_c / (c * mu - lam)
