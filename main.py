# external dep.'s
import logging
import logging.config
import os
import os.path
import pathlib
import re
import sys
import argparse
import json
import numbers

# internal dep.'s
from forecast_validation import (
    PullRequestFileType,
    VALIDATIONS_VERSION
)
from forecast_validation.validation import (
    ValidationStep,
    ValidationPerFileStep,
    ValidationRun
)
from forecast_validation.validation_logic.forecast_file_content import (
    check_forecast_retraction,
    check_new_model,
    get_all_forecast_filepaths,
    filename_match_forecast_date_check,
    validate_forecast_files
)
from forecast_validation.validation_logic.forecast_file_type import (
    check_multiple_model_names,
    check_file_locations,
    check_modified_forecasts,
    check_removed_files
)
from forecast_validation.validation_logic.github_connection import (
    establish_github_connection,
    extract_pull_request,
    determine_pull_request_type,
    get_all_models_from_repository,
    download_all_forecast_and_metadata_files
)
from forecast_validation.validation_logic.metadata import (
    get_all_metadata_filepaths,
    validate_metadata_files
)

logging.config.fileConfig("logging.conf")

# --- configurations and constants end ---

def setup_validation_run_for_pull_request(project_dir: str) -> ValidationRun:
    # load config file
    config = os.path.join(project_dir, "project-config.json")
    f = open(config)
    config_dict = json.load(f)
    f.close()
    
    steps = []
   
    # Connect to GitHub
    steps.append(ValidationStep(establish_github_connection))

    # Extract PR
    steps.append(ValidationStep(extract_pull_request))

    # Determine whether this PR is a forecast submission
    steps.append(ValidationStep(determine_pull_request_type))

    # Check if the PR tries to add to/update multiple models
    steps.append(ValidationStep(check_multiple_model_names))

    # Check the locations of some PR files to apply appropriate labels:
    #   other-files-updated, metadata-change
    steps.append(ValidationStep(check_file_locations))

    # Check if the PR has updated existing forecasts
    steps.append(ValidationStep(check_modified_forecasts))

    # Check if the PR has removed existing forecasts/metadata
    steps.append(ValidationStep(check_removed_files))

    # Get all current models from hub repository
    steps.append(ValidationStep(get_all_models_from_repository))

    # Download all forecast and metadata files
    steps.append(ValidationStep(download_all_forecast_and_metadata_files))

    # Extract filepaths for downloaded *.csv files
    steps.append(ValidationStep(get_all_forecast_filepaths))

    # Extract filepaths for downloaded *.txt files
    steps.append(ValidationStep(get_all_metadata_filepaths))

    # All forecast date checks
    steps.append(ValidationPerFileStep(filename_match_forecast_date_check))

    # All forecast format and value sanity checks
    steps.append(ValidationPerFileStep(validate_forecast_files))

    # All metadata format and value sanity checks
    steps.append(ValidationStep(validate_metadata_files))

    # Check for new team submission
    steps.append(ValidationPerFileStep(check_new_model))

    # Check updates/retractions
    steps.append(ValidationPerFileStep(check_forecast_retraction))
  
    # make new validation run
    validation_run = ValidationRun(steps)

    REPOSITORY_ROOT_ONDISK = (pathlib.Path(__file__)/".."/"..").resolve()
    FILENAME_PATTERNS: dict[PullRequestFileType, re.Pattern] = {
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
    # add initial values to store
    validation_run.store.update({
        "VALIDATIONS_VERSION": VALIDATIONS_VERSION,
        "REPOSITORY_ROOT_ONDISK": REPOSITORY_ROOT_ONDISK,
        "HUB_REPOSITORY_NAME": config_dict['hub_repository_name'],
        "HUB_MIRRORED_DIRECTORY_ROOT": (REPOSITORY_ROOT_ONDISK/"hub").resolve(),
        "PULL_REQUEST_DIRECTORY_ROOT":  (REPOSITORY_ROOT_ONDISK/"pull_request").resolve(),
        "POPULATION_DATAFRAME_PATH": os.path.join(project_dir, config_dict['location_filepath']),
        "FILENAME_PATTERNS": FILENAME_PATTERNS,
        "IS_GITHUB_ACTIONS": os.environ.get("GITHUB_ACTIONS") == "true",
        "GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME": "GH_TOKEN",
        "CONFIG_FILE": config_dict,
        "FORECAST_DATES": config_dict['forecast_dates'],
        "UPDATES_ALLOWED": config_dict['updates_allowed'],
        "AUTOMERGE": config_dict['automerge_on_passed_validation'],
        "FORECAST_FOLDER_NAME": config_dict['forecast_folder_name'],
        "SUBMISSION_FORMATTING_INSTRUCTION": config_dict["submission_formatting_instruction"]
    })

    return validation_run

def validate_from_pull_request(project_dir: str) -> bool:
    validation_run: ValidationRun = setup_validation_run_for_pull_request(project_dir)

    config = os.path.join(project_dir, "project-config.json")
    f = open(config)
    config_dict = json.load(f)
    f.close()

    if not config_dict['location_filepath'] or not config_dict['hub_repository_name'] or not config_dict['forecast_folder_name'] or not config_dict['target_groups'] or not config_dict['updates_allowed'] or not config_dict['automerge_on_passed_validation']:
        return False

    if config_dict['forecast_dates']:
        for date in config_dict['forecast_dates']:
            if type(date) != str:
                return False
            matched = bool(re.match("^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$", date))
            if not matched:
                return False
        
    if type(config_dict['location_filepath']) != str or type(config_dict['hub_repository_name']) != str or type(config_dict['forecast_folder_name']) != str:
        return False

    if type(config_dict['updates_allowed']) != bool or type(config_dict['automerge_on_passed_validation']) != bool:
        return False

    if not isinstance(config_dict, dict):
        raise RuntimeError(f"validation_config was not a dict: {config_dict}, type={type(config_dict)}")
    elif 'target_groups' not in config_dict:
        raise RuntimeError(f"validation_config did not contain 'target_groups' key: {config_dict}")
    elif not isinstance(config_dict['target_groups'], list):
        raise RuntimeError(f"'target_groups' was not a list: {config_dict['target_groups']}")

    # validate each target_group
    for target_group in config_dict['target_groups']:
        expected_keys = ['outcome_variable', 'targets', 'locations', 'quantiles']
        actual_keys = list(target_group.keys())
        if actual_keys != expected_keys:
            raise RuntimeError(f"one or more target group keys was missing. expected keys={expected_keys}, "
                               f"actual keys={actual_keys}")
        elif (not isinstance(target_group['targets'], list)) \
                or (not isinstance(target_group['locations'], list)) \
                or (not isinstance(target_group['quantiles'], list)):
            raise RuntimeError(f"one of these fields was not a list: 'targets', 'locations', or 'quantiles'. "
                               f"target_group={target_group}")
        elif not isinstance(target_group['outcome_variable'], str):
            raise RuntimeError(f"'outcome_variable' field was not a string: {target_group['outcome_variable']!r}")
        elif (not all([isinstance(target, str) for target in target_group['targets']])) or \
                (not all([isinstance(target, str) for target in target_group['locations']])):
            raise RuntimeError(f"one of these fields contained non-strings: 'targets' or 'locations'"
                               f"target_group={target_group}")
        elif not all([isinstance(quantile, numbers.Number) for quantile in target_group['quantiles']]):
            raise RuntimeError(f"'quantiles' field contained non-numbers. target_group={target_group}")
        
        for quantile in target_group['quantiles']:
            if quantile < 0 or quantile > 1:
                raise RuntimeError(f"'quantiles' field should be a vslue between 0 and 1. target_group={target_group}")


    
    validation_run.run()

    return validation_run.success
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Validate Pull Request (named arguments refer to config file)'
    )
    main_args = parser.add_argument_group("main arguments")
    main_args.add_argument('--project_dir', help='directory that contains config file at root and location_filepath key in your config file(default: validation-config.json)')
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") == "true":
        success =  validate_from_pull_request(args.project_dir)
        if success:
            print("****************** success! ******************")
        else:
            sys.exit("\n Errors found during validation...")
    else:
        # TODO: add local version
        pass
