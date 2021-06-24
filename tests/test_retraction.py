import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 
import unittest
from model_utils import *

# List of sample PRs that we want to check against
test_prs = [3448, 3342]
class ValidationRetractionTest(unittest.TestCase):
    def test_updation_with_no_new_targets(self):
        self.assertFalse(
            compare_forecasts("testfiles/old_forecast.csv", "testfiles/new_forecast.csv")['implicit-retraction'])

    def test_updation_with_new_targets(self):
        self.assertFalse(
            compare_forecasts("testfiles/old_forecast.csv", "testfiles/new_forecast_new_targets.csv")['implicit-retraction'])

    def test_updation_with_removed_targets(self):
        self.assertTrue(
            compare_forecasts("testfiles/old_forecast.csv",
                              "testfiles/new_forecast_removed_targets.csv")['implicit-retraction'])

    def test_updation_with_all_duplicates(self):
        self.assertTrue(
            compare_forecasts("testfiles/old_forecast.csv",
                              "testfiles/new_forecast_same_rows.csv")['invalid'])
    
    def test_updation_with_explicit_retractions(self):
        self.assertTrue(
            compare_forecasts("testfiles/old_forecast.csv",
                              "testfiles/new_forecast_explicit_retractions.csv")['retraction'])


if __name__ == '__main__':
    unittest.main()
