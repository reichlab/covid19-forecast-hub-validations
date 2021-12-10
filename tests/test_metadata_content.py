import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import unittest
from pathlib import Path

from forecast_validation.validation_logic.metadata import check_metadata_file

class ValidationMetadataTest(unittest.TestCase):

    #A valid metadata file is submitted
    def test_valid_metadata_content(self):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/data-processed/teamA-modelA/metadata-teamA-modelA.txt"))
        #print(is_invalid, errors)
        self.assertFalse(is_invalid)
        self.assertEqual(errors, "no errors")
    
    #A metadata file is submitted in incorrect model folder
    def test_invalid_metadata_folder(self):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/data-processed/teamD-modelD/metadata-teamD-modelA.txt"))
        #print(is_invalid, errors)
        self.assertTrue(is_invalid)
        self.assertIn("METADATA_ERROR: Model abreviation in metadata inconsistent with folder name", errors[0])

    #Metadata is not a valid yaml file
    def test_invalid_metadata_yaml_file(self):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/data-processed/teamA-modelA/metadata-teamA-modelC.txt"))
        #print(is_invalid, errors)
        self.assertTrue(is_invalid)
        self.assertIn("METADATA ERROR: Metadata YAML Format Error", errors[0])

    #A metadata file is submitted with special characters and extra space in the end of the file
    def test_invalid_metadata_file_format(self):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/data-processed/teamA-modelA/metadata-teamA-modelB.txt"))
        print(is_invalid, errors)
        self.assertTrue(is_invalid)
        self.assertIn("METADATA ERROR: Metadata YAML Format Error", errors[0])

    #A metadata file without 'model_abbr' is submitted
    def test_missing_model_abbr(self):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/data-processed/teamB-modelB/metadata-teamB-modelB.txt"))
        #print(is_invalid, errors)
        self.assertTrue(is_invalid)
        self.assertIn("METADATA_ERROR: Cannot find required key 'model_abbr'.", errors[0])

    #A valid metadata file with incorrect/inconsistent model_abbr is submitted
    def test_inconsistent_model_abbr(self):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/data-processed/teamB-modelB/metadata-teamA-modelA.txt"))
        #print(is_invalid, errors)
        self.assertTrue(is_invalid)
        self.assertIn("METADATA_ERROR: Model abreviation in metadata inconsistent with folder name for model_abbr", errors[0])
    
    #A valid metadata file with invalid license is submitted
    def test_invalid_license(self):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/data-processed/teamC-modelC/metadata-teamC-modelC.txt"))
        #print(is_invalid, errors)
        self.assertTrue(is_invalid)
        self.assertIn("'license' field must be in `./code/accepted-licenses.csv`", errors[0])

if __name__ == '__main__':
    unittest.main()