"""Parámetros del negocio. Los valores por defecto describen una cafetería tipo en quetzales."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BusinessParams:
    """Números básicos del negocio, con montos en quetzales (GTQ) y tiempos en meses.

    Los valores por defecto son supuestos creíbles para una cafetería pequeña en
    Guatemala, no datos de un negocio real. Para un escenario distinto se usa
    `dataclasses.replace(BusinessParams(), campo=valor)`.

    Attributes:
        initial_cash: Caja inicial.
        avg_ticket: Venta promedio por cliente atendido.
        unit_cost: Costo de insumos por cliente atendido.
        rent: Alquiler mensual.
        employees: Número de empleados.
        salary: Costo mensual por empleado, con prestaciones.
        utilities: Servicios mensuales (luz, agua, internet).
        other_fixed: Otros costos fijos mensuales.
        initial_inventory: Inventario inicial valorado al costo.
        spoilage_rate: Fracción del inventario restante que se pierde cada mes.
        inventory_cover: Meses de consumo esperado que se busca tener tras comprar.
        loan_amount: Saldo inicial de la deuda.
        annual_rate: Tasa de interés anual de la deuda.
        loan_term: Plazo de la deuda en meses.
        demand_start: Clientes esperados en el primer mes.
        demand_mature: Clientes esperados por mes cuando el negocio madura.
        ramp_months: Mes en que la demanda alcanza la mitad del crecimiento.
        seasonality: Amplitud relativa de la estacionalidad (pico en diciembre).
        start_month: Mes calendario de apertura (1 = enero).
        horizon: Meses simulados.
    """

    initial_cash: float = 60_000.0
    avg_ticket: float = 45.0
    unit_cost: float = 15.0
    rent: float = 9_000.0
    employees: int = 3
    salary: float = 4_500.0
    utilities: float = 3_000.0
    other_fixed: float = 1_500.0
    initial_inventory: float = 8_000.0
    spoilage_rate: float = 0.05
    inventory_cover: float = 1.2
    loan_amount: float = 100_000.0
    annual_rate: float = 0.18
    loan_term: int = 36
    demand_start: float = 700.0
    demand_mature: float = 1_600.0
    ramp_months: float = 6.0
    seasonality: float = 0.10
    start_month: int = 1
    horizon: int = 24

    @property
    def fixed_costs(self):
        """Costos fijos mensuales sin la cuota de la deuda."""
        return self.rent + self.employees * self.salary + self.utilities + self.other_fixed

    @property
    def loan_payment(self):
        """Cuota mensual constante de la deuda (sistema francés)."""
        if self.loan_amount <= 0:
            return 0.0
        r = self.annual_rate / 12
        if r == 0:
            return self.loan_amount / self.loan_term
        return self.loan_amount * r / (1 - (1 + r) ** -self.loan_term)

    @property
    def margin(self):
        """Margen de contribución por cliente atendido."""
        return self.avg_ticket - self.unit_cost

    @property
    def breakeven_customers(self):
        """Clientes por mes que cubren costos fijos y cuota de la deuda."""
        return (self.fixed_costs + self.loan_payment) / self.margin


@dataclass(frozen=True)
class CustomerParams:
    """Parámetros de la población de clientes potenciales y su red de contactos.

    Los valores por defecto son supuestos para el barrio de una cafetería tipo.

    Attributes:
        population: Clientes potenciales (nodos de la red).
        neighbors: Contactos promedio por persona en la red Watts-Strogatz.
        rewiring: Probabilidad de recableado de la red Watts-Strogatz.
        initial_customers: Clientes activos en la apertura.
        innovation: Coeficiente p de Bass (atracción por publicidad, por mes).
        imitation: Coeficiente q de Bass (boca a boca, por mes).
        mean_visits: Visitas promedio por mes de un cliente activo.
        visits_shape: Forma de la distribución gamma de visitas (menor es más dispersa).
        mean_churn: Probabilidad promedio de abandono mensual.
        churn_concentration: Concentración de la distribución beta del abandono.
        unserved_sensitivity: Aumento del abandono por cada unidad de fracción no atendida.
    """

    population: int = 1_200
    neighbors: int = 8
    rewiring: float = 0.1
    initial_customers: int = 290
    innovation: float = 0.005
    imitation: float = 0.25
    mean_visits: float = 2.0
    visits_shape: float = 2.0
    mean_churn: float = 0.08
    churn_concentration: float = 20.0
    unserved_sensitivity: float = 0.5


@dataclass(frozen=True)
class QueueParams:
    """Parámetros de la atención en mostrador de un día típico. Tiempos en minutos.

    Attributes:
        servers: Personas que atienden en mostrador.
        hourly_profile: Peso relativo de llegadas de cada hora de apertura (7:00 a 19:00).
        days_per_month: Días de apertura por mes.
        service_mean: Tiempo promedio de atención (exponencial).
        patience_mean: Tiempo promedio que un cliente tolera esperar (exponencial).
        max_queue: Clientes en cola a partir de los cuales quien llega se va sin entrar.
    """

    servers: int = 2
    hourly_profile: tuple = (1.6, 2.0, 1.3, 0.8, 0.9, 1.5, 1.4, 0.7, 0.6, 0.7, 0.8, 0.7)
    days_per_month: int = 30
    service_mean: float = 5.0
    patience_mean: float = 5.0
    max_queue: int = 6
