import json
import logging
import os
import shutil
import unittest.mock
from pathlib import Path
from unittest import TestCase, mock

from forecast_validation.validation import ValidationStepResult
from main import setup_validation_run_for_pull_request


logger = logging.getLogger(__name__)


class PullRequestTestCasesTest(TestCase):
    """
    Tests PRs in the spreadsheet [validations test cases](https://docs.google.com/spreadsheets/d/1TVe45VsBTMCkyZFiZm3v6O5AGN5q5edhg3AQXZVe-mw/edit#gid=0).
    """


    def test_all_pull_requests(self):
        """
        Tries out the idea of iterating over a list of PR tests to perform plus their expected results (errors and
        labels).
        """


        def _urlretrieve(url, filename):
            """
            `urllib.request.urlretrieve()` mock called by `download_all_forecast_and_metadata_files()` to download PR
            files to disk under "PULL_REQUEST_DIRECTORY_ROOT".
            """
            shutil.copy(url, filename)  # url = pr_file


        def _get_blob_content(repository, branch, path_name):
            """
            `forecast_validation.utilities.github.get_blob_content()` mock called by `get_existing_forecast_file()`
            """
            if not repo_file:
                raise RuntimeError(f"_get_blob_content(): repo_file is not set: {repo_file!r}")

            with open(repo_file, 'rb') as fp:
                blob_mock = unittest.mock.MagicMock(content=fp.read())
            return blob_mock


        with open('tests/prs/test-config.json') as fp:
            row_id_to_test_config = json.load(fp)
        for row_id, test_config_dict in row_id_to_test_config.items():
            pr_test_dir_name = test_config_dict['dir_name']
            config_file = test_config_dict['config_file']
            file_status = test_config_dict['file_status']
            exp_success = test_config_dict['exp_success']
            exp_labels = set(test_config_dict['exp_labels'])
            exp_comments = test_config_dict['exp_comments']
            logger.info(f'* test config run: row_id={row_id!r}, pr_test_dir_name={pr_test_dir_name!r}, '
                        f'# config_file={config_file}, # exp_labels={exp_labels!r}, exp_comments={exp_comments!r}')

            pr_test_dir = Path(f'tests/prs/{pr_test_dir_name}')
            if not pr_test_dir.exists():
                logger.error(f"test config run: skipping because pr_test_dir doesn't exist. row_id={row_id}, "
                             f"pr_test_dir={pr_test_dir}")
                continue

            pr_dir = Path(f'tests/prs/{pr_test_dir_name}/pr')  # never empty
            pr_dir_csv_files = list(pr_dir.glob('*.csv'))
            repo_dir = Path(f'tests/prs/{pr_test_dir_name}/repo')  # might be empty
            repo_dir_csv_files = list(repo_dir.glob('*.csv'))
            config_file = Path(config_file)
            if len(pr_dir_csv_files) != 1:
                logger.error(f"test config run: skipping because not exactly one pr_dir_csv_files. row_id={row_id}, "
                             f"pr_dir_csv_files={pr_dir_csv_files}")
                continue

            if repo_dir_csv_files and len(repo_dir_csv_files) != 1:
                logger.error(f"test config run: skipping because not exactly one repo_dir_csv_files. row_id={row_id}, "
                             f"repo_dir_csv_files={repo_dir_csv_files}")
                continue

            pr_file = pr_dir_csv_files[0]
            repo_file = repo_dir_csv_files[0] if repo_dir_csv_files else None
            model_name = pr_file.name[11:-4]  # e.g., 'UMass-MechBayes'
            repo_root_ondisk, hub_dir, pr_dir = _set_up_test_hub(model_name)

            # set up mocks
            github_mock = mock.MagicMock(name='Github')
            repository_mock = mock.MagicMock(name='Repository')

            pr_mock = mock.MagicMock(name='PullRequest')
            p1 = mock.MagicMock(name=pr_file.name)  # github.File.File . filename, raw_url, status
            p1.filename = f'data-processed/{model_name}/{pr_file.name}'  # relative to forecast_folder_name (repo root)
            p1.raw_url = pr_file  # passed to urllib.request.urlretrieve() by download_all_forecast_and_metadata_files()
            p1.status = file_status  # "modified", "removed"
            p1.pr_test_row_id = row_id  # used by `_get_exist_fcast_file()` above
            pr_mock.get_files = lambda: [p1]

            est_gh_conn_vsr = ValidationStepResult(success=True, to_store={"github": github_mock,
                                                                           "repository": repository_mock,
                                                                           "possible_labels": _possible_labels()})
            ext_pr_vsr = ValidationStepResult(success=True, to_store={"pull_request": pr_mock})
            get_models_vsr = ValidationStepResult(success=True, to_store={"model_names": {model_name}})
            fname_match_vsr = ValidationStepResult(success=True, comments=["✔️ Forecast date validation successful."])

            # do the body of `main.validate_from_pull_request()`
            fv_util_gh = 'forecast_validation.utilities.github'
            fv_vl_gc = 'forecast_validation.validation_logic.github_connection'
            fv_vl_ffc = 'forecast_validation.validation_logic.forecast_file_content'
            with open(config_file) as config_file_fp, \
                    mock.patch('base64.b64decode', side_effect=lambda _: _), \
                    mock.patch('urllib.request.urlretrieve', side_effect=_urlretrieve), \
                    mock.patch(f'{fv_util_gh}.get_blob_content', side_effect=_get_blob_content), \
                    mock.patch(f'{fv_vl_gc}.establish_github_connection', return_value=est_gh_conn_vsr), \
                    mock.patch(f'{fv_vl_gc}.establish_github_connection', return_value=est_gh_conn_vsr), \
                    mock.patch(f'{fv_vl_gc}.extract_pull_request', return_value=ext_pr_vsr), \
                    mock.patch(f'{fv_vl_gc}.get_all_models_from_repository', return_value=get_models_vsr), \
                    mock.patch(f'{fv_vl_ffc}.filename_match_forecast_date_check', return_value=fname_match_vsr):
                config_dict = json.load(config_file_fp)
                validation_run = setup_validation_run_for_pull_request('', config_dict)  # project_dir n/a
                validation_run.store['HUB_MIRRORED_DIRECTORY_ROOT'] = hub_dir
                validation_run.store['PULL_REQUEST_DIRECTORY_ROOT'] = pr_dir
                validation_run.store['POPULATION_DATAFRAME_PATH'] = Path('forecast_validation/static/locations.csv')
                try:
                    validation_run.run()
                except RuntimeError as rte:
                    logger.error(f"test config run: skipping because error running validation: {rte!r}")
                    continue

                # collect actual labels and comments that were set via mock calls to PullRequest.set_labels and
                # PullRequest.create_issue_comment
                act_labels = set()
                act_comments = ''
                for name, args, kwargs in pr_mock.method_calls:
                    if name == 'create_issue_comment':
                        act_comments = act_comments + args[0] + '\n\n\n'
                    elif name == 'set_labels':
                        act_labels.update(args)
                act_comments = act_comments.replace('\n', '|')

                # test results
                self.assertEqual(exp_success, validation_run.success)
                self.assertEqual(exp_labels, act_labels)
                for exp_comment in exp_comments:
                    self.assertIn(exp_comment, act_comments)

                logger.info(f"test config run: passed!")


#
# test helper functions
#

def _set_up_test_hub(model_name):
    """
    Test helper that creates and populates a hub directory for testing.
    """
    # set up test hub, copy files. e.g., /tmp/test-hub/data-processed/UMass-MechBayes/2022-02-15-UMass-MechBayes.csv
    repo_root_ondisk = Path('/tmp/test-hub')  # todo xx use tempfile
    hub_dir = repo_root_ondisk / 'hub'
    pr_dir = repo_root_ondisk / 'pull_request'
    shutil.rmtree(repo_root_ondisk, ignore_errors=True)
    os.makedirs(hub_dir)
    os.makedirs(pr_dir)
    return repo_root_ondisk, hub_dir, pr_dir


def _possible_labels():
    label_names = ['automerge', 'data-submission', 'duplicate-forecast', 'file-deletion',
                   'forecast-implicit-retractions', 'forecast-retraction', 'forecast-updated', 'metadata-change',
                   'new-team-submission', 'other-files-updated', 'passed-validation']
    return {label_name: label_name for label_name in label_names}
