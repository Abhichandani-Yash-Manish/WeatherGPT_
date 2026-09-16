"""The answering grid cell and its distance, for the marine and river point products.

A discharge or a wave height belongs to a grid cell, not to the place that was asked about. The route therefore
has to name the cell and how far it is from the requested point; docs/23 and the standing agreement require it.
The packet some adapters return states no distance, so the route computes it with the same great-circle helper
every other point product uses. This pins three things: a distance the packet already states is passed through
untouched, one it does not state is computed from the requested point and the returned cell, and a read that
states no cell yields nothing rather than a guessed number.
"""
import pytest

from weathergpt_data import product_api
from weathergpt_data.answers import distance_km

KHARAGPUR = {"latitude": 22.34601, "longitude": 87.23264}
SEA_CELL = {"latitude": 21.9, "longitude": 87.4}


def test_a_stated_distance_is_passed_through_untouched():
    coverage = {"requested_point": KHARAGPUR, "returned_grid": SEA_CELL, "grid_distance_km": 12.5}
    assert product_api._grid_distance(coverage, **KHARAGPUR) == 12.5


def test_a_distance_the_read_does_not_state_is_computed_from_the_requested_point_and_the_cell():
    coverage = {"requested_point": KHARAGPUR, "returned_grid": SEA_CELL}
    expected = round(distance_km(KHARAGPUR, SEA_CELL), 3)
    assert product_api._grid_distance(coverage, **KHARAGPUR) == expected
    assert expected > 0


def test_the_requested_point_is_taken_from_the_call_when_the_read_does_not_state_one():
    coverage = {"returned_grid": SEA_CELL}
    expected = round(distance_km(KHARAGPUR, SEA_CELL), 3)
    assert product_api._grid_distance(coverage, **KHARAGPUR) == expected


def test_a_read_that_states_no_cell_yields_nothing():
    assert product_api._grid_distance({"requested_point": KHARAGPUR}, **KHARAGPUR) is None
    assert product_api._grid_distance({"returned_grid": {"latitude": None, "longitude": None}}, **KHARAGPUR) is None
    assert product_api._grid_distance({"returned_grid": "not a cell"}, **KHARAGPUR) is None


class Stub:
    """The smallest foundation the two routes touch: one packet with records and a coverage block."""

    def __init__(self, coverage, records=None):
        self.coverage = coverage
        self.records = records if records is not None else [
            {"parameter": "wave_height", "unit": "m", "model": "stub", "value": 1.2,
             "valid_time_utc": "2026-09-17T00:00:00+00:00", "quality_flags": [], "source_locator": "$.hourly.wave_height[0]"},
        ]

    def marine(self, latitude, longitude, days=3, refresh=False):
        return {"records": self.records, "coverage": self.coverage, "limitations": [],
                "source_id": "S56", "family": "marine_forecast", "provenance": {"url": "https://example.invalid/marine"}}

    def river(self, latitude, longitude, days=3, refresh=False):
        return {"records": self.records, "coverage": self.coverage, "limitations": [],
                "source_id": "S37", "family": "river_discharge", "provenance": {"url": "https://example.invalid/flood"}}


def test_the_marine_route_names_the_cell_and_its_distance():
    view = product_api.marine(Stub({"requested_point": KHARAGPUR, "returned_grid": SEA_CELL}), **KHARAGPUR)
    data = view["data"]
    assert data["grid"] == SEA_CELL
    assert data["requested"] == KHARAGPUR
    assert data["grid_distance_km"] == round(distance_km(KHARAGPUR, SEA_CELL), 3)
    assert view["status"] == "ok"


def test_the_river_route_names_the_cell_and_its_distance_without_a_stated_requested_point():
    view = product_api.river(Stub({"returned_grid": SEA_CELL}), **KHARAGPUR)
    data = view["data"]
    assert data["grid"] == SEA_CELL
    assert data["requested"] == KHARAGPUR
    assert data["grid_distance_km"] == round(distance_km(KHARAGPUR, SEA_CELL), 3)


def test_a_wave_and_a_discharge_keep_their_own_not_established_lines():
    marine = product_api.marine(Stub({"requested_point": KHARAGPUR, "returned_grid": SEA_CELL}), **KHARAGPUR)
    river = product_api.river(Stub({"requested_point": KHARAGPUR, "returned_grid": SEA_CELL}), **KHARAGPUR)
    assert any("sea-area bulletin" in line for line in marine["not_established"])
    assert any("discharge value" in line or "gauge" in line for line in river["not_established"])

