import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import unittest
from forecast_validation.checks.forecast_file_content import compare_forecasts

# List of sample PRs that we want to check against
test_prs = [3448, 3342]


class ValidationRetractionTest(unittest.TestCase):
    def test_updation_with_no_new_targets(self):
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-value_update.csv",
            ).has_implicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-value_update.csv",
            ).has_explicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-value_update.csv",
            ).is_all_duplicate
        )
        self.assertTrue(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-value_update.csv"
            ).has_no_retraction_or_duplication
        )

    def test_updation_with_new_targets(self):
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-new_targets.csv"
            ).has_implicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-new_targets.csv"
            ).has_explicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-new_targets.csv"
            ).is_all_duplicate
        )
        self.assertTrue(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-new_targets.csv"
            ).has_no_retraction_or_duplication
        )

    def test_updation_with_removed_targets(self):
        self.assertTrue(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-implicit_retractions.csv"
            ).has_implicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-implicit_retractions.csv"
            ).has_explicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-implicit_retractions.csv"
            ).is_all_duplicate
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-implicit_retractions.csv"
            ).has_no_retraction_or_duplication
        )

    def test_updation_with_all_duplicates(self):
        self.assertTrue(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-duplicate.csv"
            ).is_all_duplicate
        )

        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-duplicate.csv"
            ).has_implicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-duplicate.csv"
            ).has_explicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-duplicate.csv"
            ).has_no_retraction_or_duplication
        )

    def test_updation_with_explicit_retractions(self):
        self.assertTrue(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-explicit_retractions.csv"
            ).has_explicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-explicit_retractions.csv"
            ).has_implicit_retraction
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-explicit_retractions.csv"
            ).is_all_duplicate
        )
        self.assertFalse(
            compare_forecasts(
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-original_forecast.csv",
                "tests/testfiles/data-processed/teamA-modelA/forecast_content-explicit_retractions.csv"
            ).has_no_retraction_or_duplication
        )



if __name__ == '__main__':
    unittest.main()
