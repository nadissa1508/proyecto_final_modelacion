# ¿Cuánto aguanta mi negocio?

Simulador de supervivencia y flujo de caja para negocios pequeños, preparado como núcleo de un SaaS de demostración. A partir de los datos que conoce el dueño estima cuántos meses aguanta la caja, cuántos clientes se necesita retener, qué estrategia conviene más (publicidad, lealtad, contratar o recortar costos fijos) y si conviene vender a crédito. El resultado es un rango de escenarios (peor, probable y mejor), no una predicción exacta. Una cafetería tipo en Guatemala sirve como caso de uso.

El modelo combina cuatro paradigmas de modelación y simulación.

| Paradigma | Módulo | Qué modela |
| --- | --- | --- |
| Dinámica de sistemas | `finance.py` | Caja, inventario, deuda y cuentas por cobrar |
| Agentes en red | `customers.py` | Clientes heterogéneos con boca a boca tipo Bass, retención y mora |
| Eventos discretos | `queue_des.py` | Cola de atención con SimPy y clientes perdidos por espera |
| Monte Carlo | `montecarlo.py` | Incertidumbre en mercado, clientes, costos, ventas y mora |

`model.py` acopla las capas mes a mes. `inputs.py` y `calibration.py` convierten los datos del dueño en parámetros del modelo, `service.py` responde cada pregunta con resultados JSON y `api.py` los expone como API REST. Los valores de la cafetería son supuestos creíbles, no datos de un negocio real, y la herramienta apoya decisiones sin sustituirlas.

## Estructura

```
src/business_sim/   Paquete del simulador, servicio y API
notebooks/          Tutoriales en orden
  01_dinamica_sistemas.ipynb
  02_agentes_red.ipynb
  03_cola_atencion.ipynb
  04_integrado_montecarlo.ipynb
  05_estrategias.ipynb
  06_morosidad.ipynb
  07_servicio_saas.ipynb
tests/              Pruebas con pytest
```

## Cómo Ejecutar

Requisitos: Python 3.14 o superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Notebooks (abrir en orden con el kernel de `.venv`):

```bash
jupyter notebook notebooks/
```

API (documentación interactiva en http://localhost:8000/docs):

```bash
uvicorn business_sim.api:app
```

Pruebas:

```bash
pytest
```

Los notebooks 04 a 07 corren miles de escenarios y tardan entre 3 y 6 minutos cada uno. En la API las preguntas largas se piden con `POST /jobs/{question}` y su resultado se consulta con `GET /jobs/{job_id}`.
