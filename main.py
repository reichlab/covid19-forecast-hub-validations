# external dep.'s
import logging
import logging.config
import os
import os.path
import pathlib
import re
import sys

# internal dep.'s
from forecast_validation import (
    VALIDATIONS_VERSION,
    REPOSITORY_ROOT_ONDISK,
    HUB_REPOSITORY_NAME,
    HUB_MIRRORED_DIRECTORY_ROOT,
    POPULATION_DATAFRAME_PATH,
    FILENAME_PATTERNS,
    IS_GITHUB_ACTIONS,
    GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME,
)
from forecast_validation.validation import (
    ValidationStep,
    ValidationPerFileStep,
    ValidationRun
)
from forecast_validation.validation_logic.forecast_file_content import (
    check_new_model,
    get_all_forecast_filepaths,
    filename_match_forecast_date_check,
    validate_forecast_files
)
from forecast_validation.validation_logic.forecast_file_type import (
    check_multiple_model_names,
    check_file_locations,
    check_modified_forecasts
)
from forecast_validation.validation_logic.github_connection import (
    establish_github_connection,
    extract_pull_request,
    determine_pull_request_type,
    get_all_models_from_repository,
    download_all_forecast_and_metadata_files
)

logging.config.fileConfig("logging.conf")

# --- configurations and constants end ---

def setup_validation_run_for_pull_request() -> ValidationRun:
    
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

    # Get all current models from hub repository
    steps.append(ValidationStep(get_all_models_from_repository))

    # Download all forecast and metadata files
    steps.append(ValidationStep(download_all_forecast_and_metadata_files))

    # Extract filepaths for downloaded *.csv files
    steps.append(ValidationStep(get_all_forecast_filepaths))

    # All forecast date checks
    steps.append(ValidationPerFileStep(filename_match_forecast_date_check))

    # All forecast format and value sanity checks
    steps.append(ValidationPerFileStep(validate_forecast_files))

    # Check for new team submission
    steps.append(ValidationPerFileStep(check_new_model))

    # make new validation run
    validation_run = ValidationRun(steps)

    # add initial values to store
    validation_run.store.update({
        "VALIDATIONS_VERSION": VALIDATIONS_VERSION,
        "REPOSITORY_ROOT_ONDISK": REPOSITORY_ROOT_ONDISK,
        "HUB_REPOSITORY_NAME": HUB_REPOSITORY_NAME,
        "HUB_MIRRORED_DIRECTORY_ROOT": HUB_MIRRORED_DIRECTORY_ROOT,
        "POPULATION_DATAFRAME_PATH": POPULATION_DATAFRAME_PATH,
        "FILENAME_PATTERNS": FILENAME_PATTERNS,
        "IS_GITHUB_ACTIONS": IS_GITHUB_ACTIONS,
        "GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME": \
            GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME,
    })

    return validation_run

def validate_from_pull_request() -> bool:
    validation_run: ValidationRun = setup_validation_run_for_pull_request()
    
    validation_run.run()

    return validation_run.success
    
if __name__ == '__main__':
    print("---------- here ----------")
    if IS_GITHUB_ACTIONS:
        success = validate_from_pull_request()
        if success:
            print("****************** success! ******************")
        else:
            sys.exit("\n Errors found during validation...")
    else:
        # TODO: add local version
        pass