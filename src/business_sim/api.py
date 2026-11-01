"""API REST del simulador.

Se ejecuta con `uvicorn business_sim.api:app`. La documentación interactiva queda en
`/docs`. Las preguntas que corren Monte Carlo se atienden como trabajos en segundo
plano: `POST /jobs/{question}` devuelve un identificador y `GET /jobs/{job_id}` el
estado y, al terminar, el resultado.
"""

import inspect
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import MISSING, fields

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, create_model

from . import service
from .inputs import BusinessInput
from .strategies import StrategyConfig, describe_strategies

QUESTIONS = {
    "survival": service.survival,
    "sales_drop": service.sales_drop,
    "retention": service.retention,
    "strategies": service.strategies,
    "sensitivity": service.sensitivity,
    "credit": service.credit,
    "full_report": service.full_report,
}
"""Preguntas disponibles como trabajos y la función del servicio que las responde."""

MAX_SCENARIOS = 5_000


def _attribute_docs(cls):
    """Devuelve {campo: descripción} de la sección Attributes del docstring de `cls`."""
    doc = inspect.getdoc(cls) or ""
    section = doc.split("Attributes:", 1)[1] if "Attributes:" in doc else ""
    docs, current = {}, None
    for line in section.splitlines():
        match = re.match(r"\s{4}(\w+): (.*)", line)
        if match:
            current = match.group(1)
            docs[current] = match.group(2).strip()
        elif current and line.startswith(" " * 8):
            docs[current] += " " + line.strip()
    return docs


def _model_from_dataclass(cls, name, overrides=None):
    """Crea un modelo Pydantic con los campos, valores por defecto y descripciones de `cls`.

    Args:
        cls: Dataclass de origen.
        name: Nombre del modelo.
        overrides: {campo: (tipo, valor por defecto o fábrica)} para reemplazar campos.
    """
    docs = _attribute_docs(cls)
    overrides = overrides or {}
    definitions = {}
    for f in fields(cls):
        if f.name in overrides:
            ann, default = overrides[f.name]
        else:
            ann = f.type
            default = f.default if f.default is not MISSING else f.default_factory()
        if callable(default) and isinstance(default, type):
            definitions[f.name] = (ann, Field(default_factory=default, description=docs.get(f.name)))
        else:
            definitions[f.name] = (ann, Field(default=default, description=docs.get(f.name)))
    return create_model(name, **definitions)


StrategyModel = _model_from_dataclass(StrategyConfig, "StrategyConfigModel")
BusinessModel = _model_from_dataclass(BusinessInput, "BusinessInputModel", {
    "hourly_profile": (list[float] | None, list(BusinessInput().hourly_profile)),
    "strategies": (StrategyModel, StrategyModel),
})


class JobRequest(BaseModel):
    """Cuerpo de `POST /jobs/{question}`."""

    business: BusinessModel = Field(default_factory=BusinessModel, description="Datos del negocio.")
    options: dict = Field(default_factory=dict, description="Opciones de la pregunta, ver GET /questions.")


def _build_input(model):
    """Convierte un `BusinessModel` en `BusinessInput` sin validar las reglas del negocio."""
    data = model.model_dump()
    data["strategies"] = StrategyConfig(**data["strategies"])
    if data["hourly_profile"] is not None:
        data["hourly_profile"] = tuple(data["hourly_profile"])
    return BusinessInput(**data)


def _valid_input(model):
    """Devuelve el `BusinessInput` de `model` o responde 422 con la lista de errores."""
    inp = _build_input(model)
    errors = inp.errors()
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})
    return inp


def _options(func):
    """Devuelve {opción: valor por defecto} de una función del servicio."""
    params = list(inspect.signature(func).parameters.values())[1:]
    return {p.name: list(p.default) if isinstance(p.default, tuple) else p.default for p in params}


def _check_options(func, options):
    """Responde 422 si `options` tiene claves desconocidas o demasiados escenarios."""
    unknown = set(options) - set(_options(func))
    if unknown:
        raise HTTPException(status_code=422, detail={"errors": [f"Opciones desconocidas: {sorted(unknown)}"]})
    for key in ("n", "n_grid"):
        if key in options and not 1 <= int(options[key]) <= MAX_SCENARIOS:
            raise HTTPException(status_code=422, detail={"errors": [f"{key} debe estar entre 1 y {MAX_SCENARIOS}."]})


_jobs = {}
_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=1)


def _update(job_id, **values):
    with _lock:
        _jobs[job_id].update(values)


def _run_job(job_id, func, inp, options):
    """Ejecuta un trabajo y guarda su resultado o su error."""
    _update(job_id, status="running", started_at=time.time())
    try:
        result = func(inp, **options)
        _update(job_id, status="done", result=result, finished_at=time.time())
    except Exception as exc:  # noqa: BLE001
        _update(job_id, status="error", error=str(exc), finished_at=time.time())


app = FastAPI(
    title="¿Cuánto aguanta mi negocio?",
    description="Simulador de supervivencia y flujo de caja para negocios pequeños.",
    version="0.2.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    """Indica que la API está activa."""
    return {"status": "ok"}


@app.get("/template")
def template():
    """Devuelve los datos de la cafetería tipo y las descripciones de las estrategias."""
    return {"business": BusinessInput().to_dict(), "strategies": describe_strategies()}


@app.get("/questions")
def questions():
    """Lista las preguntas disponibles como trabajos con su descripción y opciones."""
    return {
        name: {"description": inspect.getdoc(func).splitlines()[0], "options": _options(func)}
        for name, func in QUESTIONS.items()
    }


@app.post("/validate")
def validate(business: BusinessModel):
    """Valida los datos del negocio y devuelve la lista de errores."""
    errors = _build_input(business).errors()
    return {"valid": not errors, "errors": errors}


@app.post("/summary")
def summary(business: BusinessModel):
    """Devuelve el resumen sin incertidumbre y la calibración de clientes."""
    return service.summary(_valid_input(business))


@app.post("/jobs/{question}", status_code=202)
def create_job(question: str, request: JobRequest):
    """Crea un trabajo en segundo plano para `question` y devuelve su identificador."""
    if question not in QUESTIONS:
        raise HTTPException(status_code=404, detail=f"Pregunta desconocida. Opciones: {sorted(QUESTIONS)}")
    func = QUESTIONS[question]
    inp = _valid_input(request.business)
    _check_options(func, request.options)
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id, "question": question, "status": "queued", "created_at": time.time(),
            "started_at": None, "finished_at": None, "result": None, "error": None,
        }
    _executor.submit(_run_job, job_id, func, inp, request.options)
    return {"job_id": job_id, "question": question, "status": "queued"}


@app.get("/jobs")
def list_jobs():
    """Lista los trabajos sin sus resultados."""
    with _lock:
        return [{k: v for k, v in job.items() if k != "result"} for job in _jobs.values()]


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Devuelve el estado de un trabajo y su resultado cuando termina."""
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
        return dict(job)
