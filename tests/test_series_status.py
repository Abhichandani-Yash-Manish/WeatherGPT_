"""A read that retrieved a shape with nulls in it is unavailable, not ok.

Reported by the surfaces lane on 21 September 2026 and reproduced here: the marine provider answers with
the nearest grid point whether or not it is sea, so INLAND Patna (25.5941, 85.1376) is given a "sea cell"
3.66 km away — inside the 50 km distance guard — whose `wave_height` is null for every point. The payload
was honest and the status was not, and a surface told `ok` draws an empty figure as though it were a read.
"""
import unittest

from weathergpt_data.product_api import carries_a_value


class CarriesAValueTests(unittest.TestCase):
    def test_a_series_with_one_value_carries_one(self):
        self.assertTrue(carries_a_value({'wave_height': {'points': [{'v': None}, {'v': 1.24}]}}))

    def test_a_series_of_nulls_carries_nothing(self):
        self.assertFalse(carries_a_value({'wave_height': {'points': [{'v': None}, {'v': None}]}}))

    def test_an_empty_payload_carries_nothing(self):
        self.assertFalse(carries_a_value({}))
        self.assertFalse(carries_a_value(None))
        self.assertFalse(carries_a_value({'wave_height': {'points': []}}))

    def test_a_zero_is_a_value(self):
        """An inland cell's nulls are not zero, and a real zero is not an absence."""
        self.assertTrue(carries_a_value({'river_discharge': {'points': [{'v': 0}]}}))

    def test_one_parameter_with_a_value_is_enough(self):
        self.assertTrue(carries_a_value({'wave_period': {'points': [{'v': None}]},
                                         'wave_height': {'points': [{'v': 0.98}]}}))


if __name__ == '__main__':
    unittest.main()
