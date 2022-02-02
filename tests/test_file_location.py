import unittest
import sys
import os
from typing import Pattern
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from forecast_validation import PullRequestFileType
from forecast_validation.checks.forecast_file_type import filter_files
from unittest.mock import MagicMock
import re
import json

class ValidationFileLocationTest(unittest.TestCase):
    def valid_forecast(self, actual, forecast_file):
        self.assertTrue(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.MODEL_OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.LICENSE), forecast_file)
    
    def invalid_forecast_location(self, actual, forecast_file):
        self.assertFalse(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.MODEL_OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.LICENSE), forecast_file)

    def other_forecast(self, actual, forecast_file): 
        self.assertFalse(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.MODEL_OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.LICENSE), forecast_file)
    
    def valid_metadata_file(self, actual, forecast_file): 
        self.assertFalse(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.METADATA), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.MODEL_OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.LICENSE), forecast_file)

    def invalid_model_file(self, actual, forecast_file): 
        self.assertFalse(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.MODEL_OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.LICENSE), forecast_file)

    def valid_license(self, actual, forecast_file): 
        self.assertFalse(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.MODEL_OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.LICENSE), forecast_file)

class TestWithSetupForCovid(ValidationFileLocationTest):
    def setUp(self):
        # load config file
        config = "tests/testfiles/covid-validation-config.json"
        f = open(config)
        config_dict = json.load(f)
        f.close()
        
        # setup FILENAME_PATTERNS to access forecast_folder_name from the config file
        self.FILENAME_PATTERNS: dict[PullRequestFileType, re.Pattern] = {
            PullRequestFileType.FORECAST:
                re.compile(r"^%s/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv$" % config_dict['forecast_folder_name']),
            PullRequestFileType.METADATA:
                re.compile(r"^%s/(.+)/metadata-\1\.txt$" % config_dict['forecast_folder_name']),
            PullRequestFileType.LICENSE:
                re.compile(r"^%s/(.+)/LICENSE|license\.*\.txt$" % config_dict['forecast_folder_name']),
            PullRequestFileType.MODEL_OTHER_FS:
                re.compile(r"^%s/(.+)/.*(?<!(csv|txt))$" % config_dict['forecast_folder_name']),
            PullRequestFileType.OTHER_FS:
                re.compile(r"^%s/(.+)\.(csv|txt)$" % config_dict['forecast_folder_name']),
        }

    #A file identified as a forecast is submitted in the correct model folder with correct file name.
    def test_valid_forecast(self):
        forecast_file = MagicMock(filename =  "data-processed/teamA-modelA/2021-11-29-teamA-modelA.csv")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.valid_forecast(actual, forecast_file)

    # A file identified as a forecast is submitted but it updates files outside the data-processed folder
    def test_invalid_forecast_location(self):
        forecast_file = MagicMock(filename =  "2021-11-08-teamA-modelA.csv")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.invalid_forecast_location(actual, forecast_file)

    #A file with Incorrect File Name submitted in the correct model folder
    def test_invalid_file_name(self):
        forecast_file = MagicMock(filename =  "data-processed/teamA-modelA/ABC-2021-11-08-modelA.csv")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.other_forecast(actual, forecast_file)

    #A file identified as metadata file submitted in the correct model folder
    def test_valid_metadata_file(self):
        forecast_file = MagicMock(filename =  "data-processed/teamA-modelA/metadata-teamA-modelA.txt")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.valid_metadata_file(actual, forecast_file)

    #A file identified as metadata file submitted in incorrect model folder
    def test_invalid_metadata_file(self):
        forecast_file = MagicMock(filename =  "data-processed/teamB-modelB/metadata-teamA-modelA.txt")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.other_forecast(actual, forecast_file)

    # A file identified as a forecast is submitted but it updates files outside the data-processed folder
    def test_invalid_metadata_location(self):
        forecast_file = MagicMock(filename =  "metadata-teamA-modelA.txt")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.invalid_forecast_location(actual, forecast_file)

    #A non forecast file is submitted in the correct model folder
    def test_invalid_file(self):
        forecast_file = MagicMock(filename =  "data-processed/teamA-modelA/.gitignore")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.invalid_model_file(actual, forecast_file)

    # A valid license file is submitted in the correct model folder
    def test_valid_license(self):
        forecast_file = MagicMock(filename =  "data-processed/teamA-modelA/LICENSE.txt")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.valid_license(actual, forecast_file)

class TestWithSetupForFlu(ValidationFileLocationTest):
    def setUp(self):
       # load config file
        config = "tests/testfiles/flu-validation-config.json"
        f = open(config)
        config_dict = json.load(f)
        f.close()
        # setup FILENAME_PATTERNS to access forecast_folder_name from the config file
        self.FILENAME_PATTERNS: dict[PullRequestFileType, re.Pattern] = {
            PullRequestFileType.FORECAST:
                re.compile(r"^%s/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv$" % config_dict['forecast_folder_name']),
            PullRequestFileType.METADATA:
                re.compile(r"^%s/(.+)/metadata-\1\.txt$" % config_dict['forecast_folder_name']),
            PullRequestFileType.LICENSE:
                re.compile(r"^%s/(.+)/LICENSE|license\.*\.txt$" % config_dict['forecast_folder_name']),
            PullRequestFileType.MODEL_OTHER_FS:
                re.compile(r"^%s/(.+)/.*(?<!(csv|txt))$" % config_dict['forecast_folder_name']),
            PullRequestFileType.OTHER_FS:
                re.compile(r"^%s/(.+)\.(csv|txt)$" % config_dict['forecast_folder_name']),
        }

    #A file identified as a forecast is submitted in the correct model folder with correct file name.
    def test_valid_forecast(self):
        forecast_file = MagicMock(filename =  "data-forecasts/teamA-modelA/2021-11-29-teamA-modelA.csv")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.valid_forecast(actual, forecast_file)

    # A file identified as a forecast is submitted but it updates files outside the data-forecasts folder
    def test_invalid_forecast_location(self):
        forecast_file = MagicMock(filename =  "2021-11-08-teamA-modelA.csv")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.invalid_forecast_location(actual, forecast_file)

    #A file with Incorrect File Name submitted in the correct model folder
    def test_invalid_file_name(self):
        forecast_file = MagicMock(filename =  "data-forecasts/teamA-modelA/ABC-2021-11-08-modelA.csv")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.other_forecast(actual, forecast_file)

    #A file identified as metadata file submitted in the correct model folder
    def test_valid_metadata_file(self):
        forecast_file = MagicMock(filename =  "data-forecasts/teamA-modelA/metadata-teamA-modelA.txt")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.valid_metadata_file(actual, forecast_file)

    #A file identified as metadata file submitted in incorrect model folder
    def test_invalid_metadata_file(self):
        forecast_file = MagicMock(filename =  "data-forecasts/teamB-modelB/metadata-teamA-modelA.txt")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.other_forecast(actual, forecast_file)

    # A file identified as a forecast is submitted but it updates files outside the data-processed folder
    def test_invalid_metadata_location(self):
        forecast_file = MagicMock(filename =  "metadata-teamA-modelA.txt")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.invalid_forecast_location(actual, forecast_file)

    #A non forecast file is submitted in the correct model folder
    def test_invalid_file(self):
        forecast_file = MagicMock(filename =  "data-forecasts/teamA-modelA/.gitignore")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.invalid_model_file(actual, forecast_file)

    # A valid license file is submitted in the correct model folder
    def test_valid_license(self):
        forecast_file = MagicMock(filename =  "data-forecasts/teamA-modelA/LICENSE.txt")
        actual = filter_files([forecast_file], self.FILENAME_PATTERNS)
        self.valid_license(actual, forecast_file)


if __name__ == '__main__':
    unittest.main()
