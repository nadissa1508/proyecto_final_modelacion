"""Pruebas de `BusinessInput`."""

import json

import pytest

from business_sim.inputs import BusinessInput
from business_sim.params import BusinessParams


def test_default_is_valid_and_matches_coffee_shop():
    inp = BusinessInput()
    assert inp.errors() == []
    p, cp, qp, crp = inp.to_params()
    assert p == BusinessParams()
    assert qp.servers == 2 and crp is None


def test_errors_are_collected():
    errors = BusinessInput(unit_cost=50, servers=5, closing_hour=20).errors()
    assert len(errors) == 3


def test_from_dict_rejects_unknown_fields():
    with pytest.raises(ValueError, match="desconocidos"):
        BusinessInput.from_dict({"foo": 1})


def test_round_trip_and_json():
    inp = BusinessInput.from_dict({"credit_share": 0.3, "strategies": {"ad_cost": 500}})
    data = inp.to_dict()
    json.dumps(data)
    assert BusinessInput.from_dict(data) == inp
    assert inp.to_params()[3].credit_share == 0.3


def test_flat_profile_when_none():
    qp = BusinessInput(hourly_profile=None, opening_hour=8, closing_hour=18).to_params()[2]
    assert qp.hourly_profile == (1.0,) * 10
