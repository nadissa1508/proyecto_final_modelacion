"""Datos del negocio en lenguaje del dueño, con validación y conversión a parámetros del modelo."""

from dataclasses import asdict, dataclass, field, fields

from .calibration import calibrate_customers
from .params import BusinessParams, CreditParams, QueueParams
from .strategies import StrategyConfig

COFFEE_PROFILE = QueueParams().hourly_profile


@dataclass(frozen=True)
class BusinessInput:
    """Datos que ingresa el dueño. Los valores por defecto son los de la cafetería tipo.

    Los montos están en quetzales y los tiempos de atención en minutos. Las ventas se
    expresan como visitas de clientes por mes. `hourly_profile` da el peso relativo de las
    llegadas en cada hora de apertura; None reparte las llegadas por igual.

    Attributes:
        name: Nombre del negocio.
        initial_cash: Caja inicial.
        avg_ticket: Venta promedio por visita.
        unit_cost: Costo de insumos por visita.
        rent: Alquiler mensual.
        employees: Número de empleados, incluidos quienes atienden.
        salary: Costo mensual por empleado.
        utilities: Servicios mensuales.
        other_fixed: Otros costos fijos mensuales.
        initial_inventory: Inventario inicial al costo.
        spoilage_rate: Fracción del inventario que se pierde cada mes.
        loan_amount: Deuda inicial.
        annual_rate: Tasa de interés anual de la deuda.
        loan_term: Plazo de la deuda en meses.
        sales_start: Visitas esperadas en el primer mes.
        sales_mature: Visitas esperadas por mes cuando el negocio madura.
        ramp_months: Mes en que se alcanza la mitad del crecimiento.
        seasonality: Amplitud relativa de la estacionalidad (pico en diciembre).
        start_month: Mes calendario de apertura (1 = enero).
        visits_per_customer: Visitas promedio por mes de un cliente.
        monthly_retention: Fracción de clientes que sigue comprando cada mes.
        servers: Personas que atienden al público.
        opening_hour: Hora de apertura (0 a 23).
        closing_hour: Hora de cierre (1 a 24), mayor que la de apertura.
        hourly_profile: Peso de llegadas por hora de apertura, o None.
        days_open: Días de apertura por mes.
        service_minutes: Tiempo promedio de atención por cliente.
        patience_minutes: Tiempo promedio que un cliente tolera esperar.
        max_queue: Largo de cola a partir del cual quien llega se va.
        credit_share: Fracción de clientes a crédito (0 si solo vende al contado).
        payment_delay: Meses para cobrar una venta a crédito.
        monthly_default: Probabilidad mensual promedio de mora de un cliente a crédito.
        default_churn: Probabilidad de que un cliente en mora deje el negocio.
        horizon: Meses simulados.
        strategies: Magnitudes de las estrategias.
    """

    name: str = "Cafetería tipo"
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
    loan_amount: float = 100_000.0
    annual_rate: float = 0.18
    loan_term: int = 36
    sales_start: float = 700.0
    sales_mature: float = 1_600.0
    ramp_months: float = 6.0
    seasonality: float = 0.10
    start_month: int = 1
    visits_per_customer: float = 2.0
    monthly_retention: float = 0.92
    servers: int = 2
    opening_hour: int = 7
    closing_hour: int = 19
    hourly_profile: tuple | None = COFFEE_PROFILE
    days_open: int = 30
    service_minutes: float = 5.0
    patience_minutes: float = 5.0
    max_queue: int = 6
    credit_share: float = 0.0
    payment_delay: int = 1
    monthly_default: float = 0.05
    default_churn: float = 0.5
    horizon: int = 24
    strategies: StrategyConfig = field(default_factory=StrategyConfig)

    @classmethod
    def from_dict(cls, data):
        """Crea un `BusinessInput` desde un diccionario. Las claves ausentes toman su valor por defecto.

        Raises:
            ValueError: Si hay claves desconocidas o datos inválidos.
        """
        data = dict(data)
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Campos desconocidos: {sorted(unknown)}")
        if isinstance(data.get("strategies"), dict):
            data["strategies"] = StrategyConfig(**data["strategies"])
        if data.get("hourly_profile") is not None:
            data["hourly_profile"] = tuple(data["hourly_profile"])
        inp = cls(**data)
        inp.validate()
        return inp

    def to_dict(self):
        """Devuelve los datos como diccionario serializable."""
        d = asdict(self)
        if d["hourly_profile"] is not None:
            d["hourly_profile"] = list(d["hourly_profile"])
        return d

    def errors(self):
        """Devuelve la lista de mensajes de error de los datos. Vacía si son válidos."""
        e = []

        def check(cond, msg):
            if not cond:
                e.append(msg)

        for name in ("initial_cash", "rent", "salary", "utilities", "other_fixed", "initial_inventory", "loan_amount"):
            check(getattr(self, name) >= 0, f"{name} no puede ser negativo.")
        check(self.avg_ticket > 0, "avg_ticket debe ser mayor que 0.")
        check(0 < self.unit_cost < self.avg_ticket, "unit_cost debe ser mayor que 0 y menor que avg_ticket.")
        check(self.employees >= self.servers, "employees debe ser al menos igual a servers.")
        check(0 <= self.spoilage_rate < 1, "spoilage_rate debe estar entre 0 y 1.")
        check(0 <= self.annual_rate <= 2, "annual_rate debe estar entre 0 y 2.")
        check(self.loan_term >= 1, "loan_term debe ser al menos 1.")
        check(self.sales_start > 0 and self.sales_mature > 0, "sales_start y sales_mature deben ser mayores que 0.")
        check(self.ramp_months > 0, "ramp_months debe ser mayor que 0.")
        check(0 <= self.seasonality < 1, "seasonality debe estar entre 0 y 1.")
        check(1 <= self.start_month <= 12, "start_month debe estar entre 1 y 12.")
        check(0 < self.visits_per_customer <= 60, "visits_per_customer debe estar entre 0 y 60.")
        check(0.5 <= self.monthly_retention < 1, "monthly_retention debe estar entre 0.5 y 1.")
        check(1 <= self.servers <= 20, "servers debe estar entre 1 y 20.")
        check(0 <= self.opening_hour < self.closing_hour <= 24, "Se requiere 0 <= opening_hour < closing_hour <= 24.")
        if self.hourly_profile is not None:
            check(len(self.hourly_profile) == self.closing_hour - self.opening_hour,
                  "hourly_profile debe tener un valor por cada hora de apertura.")
            check(all(w >= 0 for w in self.hourly_profile) and sum(self.hourly_profile) > 0,
                  "hourly_profile debe tener pesos no negativos con suma mayor que 0.")
        check(1 <= self.days_open <= 31, "days_open debe estar entre 1 y 31.")
        check(self.service_minutes > 0 and self.patience_minutes > 0, "service_minutes y patience_minutes deben ser mayores que 0.")
        check(self.max_queue >= 0, "max_queue no puede ser negativo.")
        check(0 <= self.credit_share <= 1, "credit_share debe estar entre 0 y 1.")
        check(1 <= self.payment_delay <= 12, "payment_delay debe estar entre 1 y 12.")
        check(0 <= self.monthly_default < 1, "monthly_default debe estar entre 0 y 1.")
        check(0 <= self.default_churn <= 1, "default_churn debe estar entre 0 y 1.")
        check(6 <= self.horizon <= 60, "horizon debe estar entre 6 y 60.")
        s = self.strategies
        check(s.ad_cost >= 0 and s.ad_factor >= 1, "ad_cost debe ser no negativo y ad_factor al menos 1.")
        check(0 <= s.loyalty_churn_cut < 1 and 0 <= s.loyalty_discount < 1, "Las magnitudes de lealtad deben estar entre 0 y 1.")
        check(s.hires >= 1, "hires debe ser al menos 1.")
        check(0 <= s.rent_cut < 1 and 0 <= s.utilities_cut < 1, "Los recortes deben estar entre 0 y 1.")
        return e

    def validate(self):
        """Lanza `ValueError` con todos los mensajes si los datos no son válidos."""
        e = self.errors()
        if e:
            raise ValueError(" ".join(e))

    def to_params(self):
        """Convierte los datos en parámetros del modelo y calibra la población de clientes.

        Returns:
            Tupla (BusinessParams, CustomerParams, QueueParams, CreditParams | None).
        """
        self.validate()
        p = BusinessParams(
            initial_cash=self.initial_cash, avg_ticket=self.avg_ticket, unit_cost=self.unit_cost,
            rent=self.rent, employees=self.employees, salary=self.salary, utilities=self.utilities,
            other_fixed=self.other_fixed, initial_inventory=self.initial_inventory,
            spoilage_rate=self.spoilage_rate, loan_amount=self.loan_amount,
            annual_rate=self.annual_rate, loan_term=self.loan_term, demand_start=self.sales_start,
            demand_mature=self.sales_mature, ramp_months=self.ramp_months,
            seasonality=self.seasonality, start_month=self.start_month, horizon=self.horizon,
        )
        cp = calibrate_customers(
            self.sales_start, self.sales_mature, self.ramp_months, self.visits_per_customer,
            1 - self.monthly_retention, self.horizon,
        )
        hours = self.closing_hour - self.opening_hour
        qp = QueueParams(
            servers=self.servers,
            hourly_profile=tuple(self.hourly_profile) if self.hourly_profile is not None else (1.0,) * hours,
            days_per_month=self.days_open, service_mean=self.service_minutes,
            patience_mean=self.patience_minutes, max_queue=self.max_queue,
        )
        crp = None
        if self.credit_share > 0:
            crp = CreditParams(credit_share=self.credit_share, payment_delay=self.payment_delay,
                               mean_default=self.monthly_default, default_churn=self.default_churn)
        return p, cp, qp, crp
