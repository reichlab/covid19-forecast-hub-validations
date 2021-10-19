import unittest
from forecast_validation.checks.forecast_file_content import compare_forecasts

# List of sample PRs that we want to check against
test_prs = [3448, 3342]
class ValidationRetractionTest(unittest.TestCase):
    def test_updation_with_no_new_targets(self):
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/old_forecast.csv",
                "tests/testfiles/new_forecast.csv"
            ).has_implicit_retraction
        )

    def test_updation_with_new_targets(self):
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/old_forecast.csv",
                "tests/testfiles/new_forecast_new_targets.csv"
            ).has_implicit_retraction
        )

    def test_updation_with_removed_targets(self):
        self.assertTrue(
            compare_forecasts(
                "tests/testfiles/old_forecast.csv",
                "tests/testfiles/new_forecast_removed_targets.csv"
            ).has_implicit_retraction
        )

    def test_updation_with_all_duplicates(self):
        self.assertTrue(
            compare_forecasts(
                "tests/testfiles/old_forecast.csv",
                "tests/testfiles/new_forecast_same_rows.csv"
            ).is_all_duplicate
        )
    
    def test_updation_with_explicit_retractions(self):
        self.assertTrue(
            compare_forecasts(
                "tests/testfiles/old_forecast.csv",
                "tests/testfiles/new_forecast_explicit_retractions.csv"
            ).has_explicit_retraction
        )

if __name__ == '__main__':
    unittest.main()
