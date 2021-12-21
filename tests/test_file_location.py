import unittest
import sys
import os
from typing import Pattern
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from forecast_validation import FILENAME_PATTERNS
from forecast_validation import PullRequestFileType
from forecast_validation.checks.forecast_file_type import filter_files
from unittest.mock import MagicMock

class ValidationFileLocationTest(unittest.TestCase):

    #A file identified as a forecast is submitted in the correct model folder.
    def test_valid_forecast_location(self):
        forecast_file = MagicMock(filename =  "data-processed/teamA-modelA/2021-11-08-teamA-modelA.csv")
        actual = filter_files([forecast_file], FILENAME_PATTERNS)
        self.assertTrue(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)

    # A file identified as a forecast is submitted in data-processed but not model folder
    def test_invalid_forecast_location(self):
        forecast_file = MagicMock(filename =  "data-processed/2021-11-08-teamA-modelA.csv")
        actual = filter_files([forecast_file], FILENAME_PATTERNS)
        self.assertFalse(actual.get(PullRequestFileType.FORECAST),forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)

    # A file identified as a forecast is submitted but it updates files outside the data-processed folder
    def test_invalid_forecast_location_root(self):
        forecast_file = MagicMock(filename =  "2021-11-08-teamA-modelA.csv")
        actual = filter_files([forecast_file], FILENAME_PATTERNS)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)
    
    #Correct name 
    def test_valid_file_name(self):
        forecast_file = MagicMock(filename =  "data-processed/teamA-modelA/2021-11-08-teamA-modelA.csv")
        actual = filter_files([forecast_file], FILENAME_PATTERNS)
        self.assertTrue(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)

    #Incorrect name
    def test_valid_infile_name(self):
        forecast_file = MagicMock(filename =  "data-processed/teamA-modelA/ABC-2021-11-08-modelA.csv")
        actual = filter_files([forecast_file], FILENAME_PATTERNS)
        self.assertFalse(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)

    #A file identified as metadata file submitted in the correct model folder
    def test_valid_metadata_file(self):
        forecast_file = MagicMock(filename =  "data-processed/teamA-modelA/metadata-teamA-modelA.txt")
        actual = filter_files([forecast_file], FILENAME_PATTERNS)
        self.assertFalse(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.METADATA), forecast_file)

    #A file identified as metadata file submitted in incorrect model folder
    def test_invalid_metadata_file(self):
        forecast_file = MagicMock(filename =  "data-processed/teamB-modelB/metadata-teamA-modelA.txt")
        actual = filter_files([forecast_file], FILENAME_PATTERNS)
        self.assertFalse(actual.get(PullRequestFileType.FORECAST), forecast_file)
        self.assertTrue(actual.get(PullRequestFileType.OTHER_FS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.OTHER_NONFS), forecast_file)
        self.assertFalse(actual.get(PullRequestFileType.METADATA), forecast_file)

if __name__ == '__main__':
    unittest.main()
