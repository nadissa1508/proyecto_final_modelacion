"""Pruebas de la API con el cliente de pruebas de FastAPI."""

import time

from fastapi.testclient import TestClient

from business_sim.api import app

client = TestClient(app)


def test_health_template_questions():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/template").json()["business"]["name"] == "Cafetería tipo"
    assert "full_report" in client.get("/questions").json()


def test_validate_and_summary_errors():
    r = client.post("/validate", json={"unit_cost": 60})
    assert r.json()["valid"] is False
    assert client.post("/summary", json={"servers": 9}).status_code == 422
    assert client.post("/summary", json={"avg_ticket": "abc"}).status_code == 422


def test_job_errors():
    assert client.post("/jobs/foo", json={}).status_code == 404
    assert client.post("/jobs/survival", json={"options": {"bad": 1}}).status_code == 422
    assert client.post("/jobs/survival", json={"options": {"n": 0}}).status_code == 422
    assert client.get("/jobs/none").status_code == 404


def test_job_runs_until_done():
    job = client.post("/jobs/survival", json={"options": {"n": 6}}).json()
    for _ in range(300):
        state = client.get(f"/jobs/{job['job_id']}").json()
        if state["status"] in ("done", "error"):
            break
        time.sleep(0.5)
    assert state["status"] == "done"
    assert 0 <= state["result"]["probability_survive"] <= 1
