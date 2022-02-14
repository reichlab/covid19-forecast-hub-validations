import unittest
import sys
import os
from typing import Pattern
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from forecast_validation import PullRequestFileType
from forecast_validation.validation_logic.forecast_file_content import validate_forecast_files
from forecast_validation.validation_logic.forecast_file_content import filename_match_forecast_date_check
from unittest.mock import MagicMock
import re
import json
import datetime
import pytz

class ValidationFileContentTest(unittest.TestCase):
        def late_submission(store: dict[str, Any], file: set[os.PathLike]):
            success: bool = True
            basename: str = os.path.basename(file)
                file_forecast_date = datetime.datetime.strptime(
                        os.path.basename(basename)[:10], "%Y-%m-%d"
                ).date()

                # forecast dates must be <1day within each other
                today = datetime.datetime.now(
                        pytz.timezone('US/Eastern')
                ).date()

                if (store["HUB_REPOSITORY_NAME"] == "cdcepi/Flusight-forecast-data"):
                        if today - file_forecast_date > datetime.timedelta(days=1):
                                success = False
                else:
                         # covid hub
                        if abs(file_forecast_date - today) > datetime.timedelta(days=1):
                                success = False
                return success
        
        def check_quantile_values(store: dict[str, Any], file: list[os.PathLike]):
                self.assertFalse() 



class TestWithSetupForCovid(ValidationFileContentTest):
    def setUp(self):
        # load config file
        config = "tests/testfiles/covid-validation-config.json"
        f = open(config)
        config_dict = json.load(f)
        f.close()
    
class TestWithSetupForFlu(ValidationFileContentTest):
    def setUp(self):
       # load config file
        config = "tests/testfiles/flu-validation-config.json"
        f = open(config)
        config_dict = json.load(f)
        f.close()

if __name__ == '__main__':
    unittest.main()
