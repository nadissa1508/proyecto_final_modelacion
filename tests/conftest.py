"""Datos compartidos por las pruebas."""

import pytest

from business_sim.params import BusinessParams, CustomerParams, QueueParams
from business_sim.queue_des import loss_table


@pytest.fixture(scope="session")
def params():
    """Parámetros por defecto de la cafetería tipo."""
    return BusinessParams(), CustomerParams(), QueueParams()


@pytest.fixture(scope="session")
def table(params):
    """Tabla de pérdida reducida para pruebas rápidas."""
    return loss_table(params[2], list(range(0, 201, 20)), [1, 2, 3], days=5, seed=0)
