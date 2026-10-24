"""Capa de agentes: clientes heterogéneos con boca a boca tipo Bass sobre una red."""

import networkx as nx
import numpy as np
import pandas as pd


class CustomerPopulation:
    """Población de clientes potenciales conectados en una red Watts-Strogatz.

    Cada agente está activo o inactivo y tiene su propia tasa de visitas (gamma) y
    probabilidad de abandono (beta). Un inactivo se activa con probabilidad
    1 - exp(-(p + q f)), donde f es la fracción de sus contactos que están activos.

    Args:
        cparams: `CustomerParams` de la población.
        rng: `numpy.random.Generator` o semilla.
    """

    def __init__(self, cparams, rng=None):
        self.cp = cparams
        self.rng = np.random.default_rng(rng)
        n = cparams.population
        seed = int(self.rng.integers(2**31))
        self.graph = nx.watts_strogatz_graph(n, cparams.neighbors, cparams.rewiring, seed=seed)
        self.adjacency = nx.to_scipy_sparse_array(self.graph, format="csr")
        self.degree = np.maximum(self.adjacency.sum(axis=1), 1)
        self.visit_rate = self.rng.gamma(
            cparams.visits_shape, cparams.mean_visits / cparams.visits_shape, n)
        a = cparams.mean_churn * cparams.churn_concentration
        b = (1 - cparams.mean_churn) * cparams.churn_concentration
        self.churn = self.rng.beta(a, b, n)
        self.active = np.zeros(n, dtype=bool)
        self.active[self.rng.choice(n, cparams.initial_customers, replace=False)] = True

    def step(self, season=1.0, unserved_share=0.0, innovation=None, churn_factor=1.0):
        """Avanza un mes y devuelve sus conteos.

        El orden es adopción, visitas de los activos y abandono al cierre del mes.

        Args:
            season: Multiplicador estacional de las visitas.
            unserved_share: Fracción de visitas del mes que no se atendieron.
            innovation: Coeficiente p del mes. Si es None se usa el de `cparams`.
            churn_factor: Multiplicador del abandono individual (lealtad < 1).

        Returns:
            Diccionario con active, new, visits y churned.
        """
        p = self.cp.innovation if innovation is None else innovation
        f = self.adjacency @ self.active / self.degree
        prob = 1 - np.exp(-(p + self.cp.imitation * f))
        new = ~self.active & (self.rng.random(self.active.size) < prob)
        self.active |= new

        visits = int(self.rng.poisson(self.visit_rate[self.active] * season).sum())
        active = int(self.active.sum())

        churn = np.clip(self.churn * churn_factor + self.cp.unserved_sensitivity * unserved_share, 0, 1)
        churned = self.active & (self.rng.random(self.active.size) < churn)
        self.active &= ~churned
        return {"active": active, "new": int(new.sum()), "visits": visits, "churned": int(churned.sum())}


def simulate_customers(cparams, season, rng=None):
    """Simula la población de clientes durante `len(season)` meses sin restricción de cola.

    Args:
        cparams: `CustomerParams` de la población.
        season: Multiplicador estacional de cada mes.
        rng: `numpy.random.Generator` o semilla.

    Returns:
        `DataFrame` indexado por mes (1 a n) con active, new, visits y churned.
    """
    pop = CustomerPopulation(cparams, rng)
    df = pd.DataFrame([pop.step(s) for s in season])
    df.index = pd.RangeIndex(1, len(df) + 1, name="month")
    return df
