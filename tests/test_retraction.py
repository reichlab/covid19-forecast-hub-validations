import unittest
from model_utils import *


class ValidationRetractionTest(unittest.TestCase):
    def test_updation_with_no_new_targets(self):
        self.assertFalse(
            compare_forecasts("testfiles/old_forecast.csv", "testfiles/new_forecast.csv"))

    def test_updation_with_new_targets(self):
        self.assertTrue(
            compare_forecasts("testfiles/old_forecast.csv", "testfiles/new_forecast_new_targets.csv"))


if __name__ == '__main__':
    unittest.main()
