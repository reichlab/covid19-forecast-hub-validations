import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import unittest
from pathlib import Path
import json

from forecast_validation.validation_logic.metadata import check_metadata_file

class ValidationMetadataTest(unittest.TestCase):

    #A valid hub metadata file is submitted
    def valid_metadata_content(self, folder_name):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/"+folder_name+"/teamF-modelF/metadata-teamF-modelF.txt"))
        self.assertFalse(is_invalid)
        self.assertEqual(errors, "no errors")

    #A metadata file is submitted in incorrect model folder
    def invalid_metadata_folder(self, folder_name):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/"+folder_name+"/teamD-modelD/metadata-teamD-modelA.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA_ERROR: Model abreviation in metadata inconsistent with folder name", errors[0])

    #Metadata is not a valid yaml file
    def invalid_metadata_yaml_file(self, folder_name):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/"+folder_name+"/teamA-modelA/metadata-teamA-modelC.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA ERROR: Metadata YAML Format Error", errors[0])

    #A metadata file is submitted with special characters and extra space in the end of the file
    def invalid_metadata_file_format(self, folder_name):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/"+folder_name+"/teamE-modelE/metadata-teamE-modelE.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA ERROR: Metadata YAML Format Error", errors[0])
        
    #A metadata file without 'model_abbr' is submitted
    def missing_model_abbr(self, folder_name):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/"+folder_name+"/teamB-modelB/metadata-teamB-modelB.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA_ERROR: Cannot find required key 'model_abbr'.", errors[0])

    #A valid metadata file with incorrect/inconsistent model_abbr is submitted
    def inconsistent_model_abbr(self, folder_name):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/"+folder_name+"/teamB-modelB/metadata-teamA-modelA.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA_ERROR: Model abreviation in metadata inconsistent with folder name for model_abbr", errors[0])
    
    #A valid metadata file with invalid license is submitted
    def invalid_license(self, folder_name):
        is_invalid, errors = check_metadata_file(Path("tests/testfiles/"+folder_name+"/teamC-modelC/metadata-teamC-modelC.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("'license' field must be in `./code/accepted-licenses.csv`", errors[0])

class TestWithSetupForCovid(ValidationMetadataTest):
    def setUp(self):
        config = "tests/testfiles/covid-validation-config.json"
        f = open(config)
        self.config_dict = json.load(f)
        f.close()

    def test_valid_metadata_content(self):
        self.valid_metadata_content(self.config_dict['forecast_folder_name'])

    def test_invalid_metadata_folder(self):
        self.invalid_metadata_folder(self.config_dict['forecast_folder_name'])

    #Metadata is not a valid yaml file
    def test_invalid_metadata_yaml_file(self):
        self.invalid_metadata_yaml_file(self.config_dict['forecast_folder_name'])

    #A metadata file is submitted with special characters and extra space in the end of the file
    def test_invalid_metadata_file_format(self):
        self.invalid_metadata_file_format(self.config_dict['forecast_folder_name'])

    def test_missing_model_abbr(self):
        self.missing_model_abbr(self.config_dict['forecast_folder_name'])

    def test_inconsistent_model_abbr(self):
        self.inconsistent_model_abbr(self.config_dict['forecast_folder_name'])
    
    def test_invalid_license(self):
        self.invalid_license(self.config_dict['forecast_folder_name'])
    

class TestWithSetupForFlu(ValidationMetadataTest):
    def setUp(self):
       # load config file
        config = "tests/testfiles/flu-validation-config.json"
        f = open(config)
        self.config_dict = json.load(f)
        f.close()

    def test_valid_metadata_content(self):
        self.valid_metadata_content(self.config_dict['forecast_folder_name'])

    def test_invalid_metadata_folder(self):
        self.invalid_metadata_folder(self.config_dict['forecast_folder_name'])

    #Metadata is not a valid yaml file
    def test_invalid_metadata_yaml_file(self):
        self.invalid_metadata_yaml_file(self.config_dict['forecast_folder_name'])

    #A metadata file is submitted with special characters and extra space in the end of the file
    def test_invalid_metadata_file_format(self):
        self.invalid_metadata_file_format(self.config_dict['forecast_folder_name'])

    def test_missing_model_abbr(self):
        self.missing_model_abbr(self.config_dict['forecast_folder_name'])

    def test_inconsistent_model_abbr(self):
        self.inconsistent_model_abbr(self.config_dict['forecast_folder_name'])
    
    def test_invalid_license(self):
        self.invalid_license(self.config_dict['forecast_folder_name'])

if __name__ == '__main__':
    unittest.main()

