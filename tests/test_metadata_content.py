import os
import sys
from unittest.mock import MagicMock, patch


sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import unittest
from pathlib import Path
import json

from forecast_validation.validation_logic.metadata import check_metadata_file, _compare_team_model_desig_dicts, \
    _team_model_desig_dict_from_pr, _team_model_desig_dict_from_repo, validate_metadata_files


class ValidationMetadataTest(unittest.TestCase):

    # A valid hub metadata file is submitted
    def valid_metadata_content(self, folder_name):
        is_invalid, errors = check_metadata_file(
            Path("tests/testfiles/" + folder_name + "/teamF-modelF/metadata-teamF-modelF.txt"))
        self.assertFalse(is_invalid)
        self.assertEqual(errors, "no errors")


    # A metadata file is submitted in incorrect model folder
    def invalid_metadata_folder(self, folder_name):
        is_invalid, errors = check_metadata_file(
            Path("tests/testfiles/" + folder_name + "/teamD-modelD/metadata-teamD-modelA.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA_ERROR: Model abreviation in metadata inconsistent with folder name", errors[0])


    # Metadata is not a valid yaml file
    def invalid_metadata_yaml_file(self, folder_name):
        is_invalid, errors = check_metadata_file(
            Path("tests/testfiles/" + folder_name + "/teamA-modelA/metadata-teamA-modelC.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA ERROR: Metadata YAML Format Error", errors[0])


    # A metadata file is submitted with special characters and extra space in the end of the file
    def invalid_metadata_file_format(self, folder_name):
        is_invalid, errors = check_metadata_file(
            Path("tests/testfiles/" + folder_name + "/teamE-modelE/metadata-teamE-modelE.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA ERROR: Metadata YAML Format Error", errors[0])


    # A metadata file without 'model_abbr' is submitted
    def missing_model_abbr(self, folder_name):
        is_invalid, errors = check_metadata_file(
            Path("tests/testfiles/" + folder_name + "/teamB-modelB/metadata-teamB-modelB.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA_ERROR: Cannot find required key 'model_abbr'.", errors[0])


    # A valid metadata file with incorrect/inconsistent model_abbr is submitted
    def inconsistent_model_abbr(self, folder_name):
        is_invalid, errors = check_metadata_file(
            Path("tests/testfiles/" + folder_name + "/teamB-modelB/metadata-teamA-modelA.txt"))
        self.assertTrue(is_invalid)
        self.assertIn("METADATA_ERROR: Model abreviation in metadata inconsistent with folder name for model_abbr",
                      errors[0])


    # A valid metadata file with invalid license is submitted
    def invalid_license(self, folder_name):
        is_invalid, errors = check_metadata_file(
            Path("tests/testfiles/" + folder_name + "/teamC-modelC/metadata-teamC-modelC.txt"))
        self.assertTrue(is_invalid)
        self.assertIn(
            "METADATA ERROR: tests/testfiles/" + folder_name + "/teamC-modelC/metadata-teamC-modelC.txt 'license' field must be in `accepted-licenses.csv` 'license' column 'lmn'",
            errors[0])


    # A valid metadata file with more than one primary model
    def invalid_model_designation(self, folder_name):
        is_invalid, errors = check_metadata_file(
            Path("tests/testfiles/" + folder_name + "/CU-modelA/metadata-CU-modelA.txt"))
        self.assertTrue(is_invalid)
        self.assertIn('METADATA ERROR: CU has more than 1 model designated as "primary"', errors[0])


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


    # Metadata is not a valid yaml file
    def test_invalid_metadata_yaml_file(self):
        self.invalid_metadata_yaml_file(self.config_dict['forecast_folder_name'])


    # A metadata file is submitted with special characters and extra space in the end of the file
    def test_invalid_metadata_file_format(self):
        self.invalid_metadata_file_format(self.config_dict['forecast_folder_name'])


    def test_missing_model_abbr(self):
        self.missing_model_abbr(self.config_dict['forecast_folder_name'])


    def test_inconsistent_model_abbr(self):
        self.inconsistent_model_abbr(self.config_dict['forecast_folder_name'])


    def test_invalid_license(self):
        self.invalid_license(self.config_dict['forecast_folder_name'])


    def test_invalid_model_designation(self):
        self.invalid_model_designation(self.config_dict['forecast_folder_name'])


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


    # Metadata is not a valid yaml file
    def test_invalid_metadata_yaml_file(self):
        self.invalid_metadata_yaml_file(self.config_dict['forecast_folder_name'])


    # A metadata file is submitted with special characters and extra space in the end of the file
    def test_invalid_metadata_file_format(self):
        self.invalid_metadata_file_format(self.config_dict['forecast_folder_name'])


    def test_missing_model_abbr(self):
        self.missing_model_abbr(self.config_dict['forecast_folder_name'])


    def test_inconsistent_model_abbr(self):
        self.inconsistent_model_abbr(self.config_dict['forecast_folder_name'])


    def test_invalid_license(self):
        self.invalid_license(self.config_dict['forecast_folder_name'])


    def test_invalid_model_designation(self):
        self.invalid_model_designation(self.config_dict['forecast_folder_name'])


class MetadataTeamModelDesignationTest(unittest.TestCase):
    """
    Tests the `team_model_designation` metadata field.
    """


    def test__compare_team_model_desig_dicts(self):
        model_repo_pr_desig_dicts_exp_results = [  # repo_dict, pr_dict, exp_result
            ({'teamA': {'model1': 'secondary', 'model2': 'secondary'}},
             {'teamA': {'model1': 'secondary'}},
             ''),
            ({'teamA': {'model1': 'secondary', 'model2': 'secondary'}},
             {'teamA': {'model1': 'primary'}},
             ''),
            ({'teamA': {'model1': 'secondary', 'model2': 'secondary'}},
             {'teamA': {'model1': 'primary', 'model2': 'primary'}},
             "❌ PR merge would result in team_model_designations with more than one 'primary' model for the same "
             "team: 'teamA-model1', 'teamA-model2'"),
            ({'teamA': {'model1': 'secondary', 'model2': 'secondary'}},
             {'teamA': {'model1': 'primary', 'model2': 'primary'},
              'teamB': {'model3': 'primary', 'model4': 'primary'}},
             "❌ PR merge would result in team_model_designations with more than one 'primary' model for the same "
             "team: 'teamA-model1', 'teamA-model2', 'teamB-model3', 'teamB-model4'"),
            ({'teamA': {'model1': 'primary', 'model2': 'secondary'}},
             {'teamA': {'model1': 'secondary'}},
             ''),
            ({'teamA': {'model1': 'primary', 'model2': 'secondary'}},
             {'teamA': {'model1': 'primary'}},
             ''),
            ({'teamA': {'model1': 'primary', 'model2': 'secondary'}},
             {'teamA': {'model2': 'primary'}},
             "❌ PR merge would result in team_model_designations with more than one 'primary' model for the same "
             "team: 'teamA-model1', 'teamA-model2'"),
            ({'teamA': {'model1': 'primary', 'model2': 'secondary'}},
             {'teamA': {'model1': 'primary', 'model2': 'primary'}},
             "❌ PR merge would result in team_model_designations with more than one 'primary' model for the same "
             "team: 'teamA-model1', 'teamA-model2'"),
            ({'teamA': {'model1': 'primary', 'model2': 'secondary'}},
             {'teamA': {'model1': 'secondary', 'model2': 'primary'}},
             ''),
        ]
        for repo_dict, pr_dict, exp_result in model_repo_pr_desig_dicts_exp_results:
            act_result = _compare_team_model_desig_dicts(repo_dict, pr_dict)
            self.assertEqual(exp_result, act_result)


    def test__team_model_desig_dict_from_pr(self):
        store = {"metadata_files": [  # from PR
            Path('tests/testfiles/model-designation/COVIDhub-4_week_ensemble/metadata-COVIDhub-4_week_ensemble.txt'),
            Path('tests/testfiles/model-designation/COVIDhub-baseline/metadata-COVIDhub-baseline.txt'),
        ]}
        act_result = _team_model_desig_dict_from_pr(store)
        self.assertEqual({'COVIDhub': {'4_week_ensemble': 'other', 'baseline': 'secondary'}},
                         act_result)


    def test__team_model_desig_dict_from_repo(self):
        def _get_contents(path):
            p1 = MagicMock()
            p1.path = 'data-processed/COVIDhub-4_week_ensemble'
            p1.name = 'COVIDhub-4_week_ensemble'
            p2 = MagicMock()
            p2.path = 'data-processed/COVIDhub-baseline'
            p2.name = 'COVIDhub-baseline'
            return {'data-processed': [p1, p2],
                    'data-processed/COVIDhub-4_week_ensemble/metadata-COVIDhub-4_week_ensemble.txt':
                        MagicMock(decoded_content='content_4wens'),
                    'data-processed/COVIDhub-baseline/metadata-COVIDhub-baseline.txt':
                        MagicMock(decoded_content='content_base')}[path]


        def _safe_load(yaml_content):
            return {'content_4wens': {'model_name': '4_week_ensemble', 'team_model_designation': 'other'},
                    'content_base': {'model_name': 'baseline', 'team_model_designation': 'secondary'},
                    }[yaml_content]  # metadata


        repository = MagicMock()
        repository.get_contents.side_effect = _get_contents
        store = {"repository": repository, "FORECAST_FOLDER_NAME": "data-processed"}
        with patch('yaml.safe_load', side_effect=_safe_load):
            act_result = _team_model_desig_dict_from_repo(store, {'COVIDhub'})
        self.assertEqual({'COVIDhub': {'4_week_ensemble': 'other', 'baseline': 'secondary'}},
                         act_result)


    def test_validate_metadata_files_calls__validate_team_model_designation(self):
        with patch('forecast_validation.validation_logic.metadata._validate_team_model_designation',
                   return_value=(False, 'foo')) as fcn_mock:
            validate_metadata_files({"metadata_files": []})  # store
            fcn_mock.assert_called_once()


#
# main
#

if __name__ == '__main__':
    unittest.main()
