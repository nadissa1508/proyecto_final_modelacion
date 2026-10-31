"""Capa de agentes: clientes heterogéneos con boca a boca tipo Bass sobre una red."""

import networkx as nx
import numpy as np
import pandas as pd


class CustomerPopulation:
    """Población de clientes potenciales conectados en una red Watts-Strogatz.

    Cada agente está activo o inactivo y tiene su propia tasa de visitas (gamma) y
    probabilidad de abandono (beta). Un inactivo se activa con probabilidad
    1 - exp(-(p + q f)), donde f es la fracción de sus contactos que están activos.

    Si `crparams.credit_share > 0`, una fracción de agentes compra a crédito y cada uno
    tiene su probabilidad de mora mensual (beta). Los sorteos de crédito usan un
    generador hijo, por lo que no alteran la secuencia del resto del modelo.

    Args:
        cparams: `CustomerParams` de la población.
        rng: `numpy.random.Generator` o semilla.
        crparams: `CreditParams` opcional.
    """

    def __init__(self, cparams, rng=None, crparams=None):
        self.cp = cparams
        self.crp = crparams
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
        self.credit = None
        if crparams is not None and crparams.credit_share > 0:
            self.credit_rng = self.rng.spawn(1)[0]
            self.credit = self.credit_rng.random(n) < crparams.credit_share
            if crparams.mean_default > 0:
                a = crparams.mean_default * crparams.default_concentration
                b = (1 - crparams.mean_default) * crparams.default_concentration
                self.default_prob = self.credit_rng.beta(a, b, n)
            else:
                self.default_prob = np.zeros(n)

    def step(self, season=1.0, unserved_share=0.0, innovation=None, churn_factor=1.0):
        """Avanza un mes y devuelve sus conteos.

        El orden es adopción, visitas de los activos, mora de los clientes a crédito que
        compraron y abandono al cierre del mes. Quien cae en mora pierde el crédito y deja
        el negocio con probabilidad `default_churn`.

        Args:
            season: Multiplicador estacional de las visitas.
            unserved_share: Fracción de visitas del mes que no se atendieron.
            innovation: Coeficiente p del mes. Si es None se usa el de `cparams`.
            churn_factor: Multiplicador del abandono individual (lealtad < 1).

        Returns:
            Diccionario con active, new, visits, churned, credit_visits (visitas a
            crédito), default_visits (visitas a crédito que no se cobrarán) y defaulters.
        """
        p = self.cp.innovation if innovation is None else innovation
        f = self.adjacency @ self.active / self.degree
        prob = 1 - np.exp(-(p + self.cp.imitation * f))
        new = ~self.active & (self.rng.random(self.active.size) < prob)
        self.active |= new

        idx = np.flatnonzero(self.active)
        agent_visits = self.rng.poisson(self.visit_rate[idx] * season)
        visits = int(agent_visits.sum())
        active = int(self.active.sum())

        credit_visits = default_visits = 0
        leave = np.empty(0, dtype=int)
        defaulted = np.empty(0, dtype=int)
        if self.credit is not None:
            buyer = self.credit[idx] & (agent_visits > 0)
            credit_visits = int(agent_visits[self.credit[idx]].sum())
            fails = buyer & (self.credit_rng.random(idx.size) < self.default_prob[idx])
            default_visits = int(agent_visits[fails].sum())
            defaulted = idx[fails]
            self.credit[defaulted] = False
            leave = defaulted[self.credit_rng.random(defaulted.size) < self.crp.default_churn]

        churn = np.clip(self.churn * churn_factor + self.cp.unserved_sensitivity * unserved_share, 0, 1)
        churned = self.active & (self.rng.random(self.active.size) < churn)
        self.active &= ~churned
        self.active[leave] = False
        return {
            "active": active, "new": int(new.sum()), "visits": visits, "churned": int(churned.sum()),
            "credit_visits": credit_visits, "default_visits": default_visits, "defaulters": int(defaulted.size),
        }


def simulate_customers(cparams, season, rng=None, crparams=None):
    """Simula la población de clientes durante `len(season)` meses sin restricción de cola.

    Args:
        cparams: `CustomerParams` de la población.
        season: Multiplicador estacional de cada mes.
        rng: `numpy.random.Generator` o semilla.
        crparams: `CreditParams` opcional.

    Returns:
        `DataFrame` indexado por mes (1 a n) con las claves de `CustomerPopulation.step`.
    """
    pop = CustomerPopulation(cparams, rng, crparams)
    df = pd.DataFrame([pop.step(s) for s in season])
    df.index = pd.RangeIndex(1, len(df) + 1, name="month")
    return df
