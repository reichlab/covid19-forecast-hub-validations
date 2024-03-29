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

        def late_submission(self, HUB_REPOSITORY_NAME, file):
                success = True
                basename = file
                file_forecast_date = datetime.datetime.strptime(
                        os.path.basename(basename)[:10], "%Y-%m-%d"
                ).date()

                # forecast dates must be <1day within each other
                today = datetime.datetime.now(
                        pytz.timezone('US/Eastern')
                ).date()

                if (HUB_REPOSITORY_NAME == "cdcepi/Flusight-forecast-data"):
                        if today - file_forecast_date > datetime.timedelta(days=1):
                                success = False
                else:
                         # covid hub
                        if abs(file_forecast_date - today) > datetime.timedelta(days=1):
                                success = False
                return success

        def not_a_late_submission(self, success):
                self.assertTrue(success)

        def a_late_submission(self, success):
                self.assertFalse(success)

class TestWithSetupForCovid(ValidationFileContentTest):

        def setUp(self):
                # load config file
                config = "tests/testfiles/covid-validation-config.json"
                f = open(config)
                config_dict = json.load(f)
                f.close()

                self.HUB_REPOSITORY_NAME = config_dict['hub_repository_name']

                self.today = str(datetime.datetime.now(
                        pytz.timezone('US/Eastern')
                ).date())

                self.late =  str(datetime.datetime.today() + datetime.timedelta(days=2))

                self.early =  str(datetime.datetime.today() - datetime.timedelta(days=2))

                self.valid_early =  str(datetime.datetime.today() - datetime.timedelta(days=1))

                self.valid_late =  str(datetime.datetime.today() + datetime.timedelta(days=1))
        
        def test_valid_submissions(self):
                # on time submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-processed/teamA-modelA/"+self.today+"-teamA-modelA.csv")
                self.not_a_late_submission(success)

                # 1-day late submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-processed/teamA-modelA/"+self.valid_early+"-teamA-modelA.csv")
                self.not_a_late_submission(success)
                
                # 1-day early submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-processed/teamA-modelA/"+self.valid_late+"-teamA-modelA.csv")
                self.not_a_late_submission(success)

        def test_invalid_submission(self):
                # 2-day early submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-processed/teamA-modelA/"+self.late+"-teamA-modelA.csv")
                self.a_late_submission(success)

                # 2-day late submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-processed/teamA-modelA/"+self.early+"-teamA-modelA.csv")
                self.a_late_submission(success)
    
class TestWithSetupForFlu(ValidationFileContentTest):
        def setUp(self):
                # load config file
                config = "tests/testfiles/flu-validation-config.json"
                f = open(config)
                config_dict = json.load(f)
                f.close()

                self.HUB_REPOSITORY_NAME = config_dict['hub_repository_name']

                self.today = str(datetime.datetime.now(
                        pytz.timezone('US/Eastern')
                ).date())

                self.late =  str(datetime.datetime.today() + datetime.timedelta(days=2))

                self.early =  str(datetime.datetime.today() - datetime.timedelta(days=2))

                self.valid_early =  str(datetime.datetime.today() - datetime.timedelta(days=1))

                self.valid_late =  str(datetime.datetime.today() + datetime.timedelta(days=1))
        

        def test_valid_submission(self):
                # 2-day early submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-forecasts/teamA-modelA/"+self.late+"-teamA-modelA.csv")
                self.not_a_late_submission(success)

                # 1-day late submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-forecasts/teamA-modelA/"+self.valid_early+"-teamA-modelA.csv")
                self.not_a_late_submission(success)
               
                # 1-day early submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-forecasts/teamA-modelA/"+self.valid_late+"-teamA-modelA.csv")
                self.not_a_late_submission(success)
                
                # on time submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-forecasts/teamA-modelA/"+self.today+"-teamA-modelA.csv")
                self.not_a_late_submission(success)
                
        def test_invaid_submission(self):
                # 2-day late submission
                success = self.late_submission(self.HUB_REPOSITORY_NAME, "data-forecasts/teamA-modelA/"+self.early+"-teamA-modelA.csv")
                self.a_late_submission(success)
                

if __name__ == '__main__':
    unittest.main()
