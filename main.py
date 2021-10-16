# external dep.'s
import logging
import logging.config
import os
import os.path
import pathlib
import re
import sys

# internal dep.'s
from forecast_validation import PullRequestFileType
from forecast_validation.validation import (
    ValidationStep,
    ValidationRun
)
from forecast_validation.validation_logic.github_connection import (
    establish_github_connection,
    extract_pull_request,
    determine_pull_request_type,
    get_all_models_from_repository,
    download_all_forecast_and_metadata_files
)
from forecast_validation.validation_logic.forecast_filetype import (
    check_multiple_model_names,
    check_file_locations,
    check_modified_forecasts
)
from forecast_validation.validation_logic.forecast_file import (
    get_all_forecast_filepaths
)


# --- configurations and constants ---

VALIDATIONS_VERSION: int = 4 # as of 10/16/2021
METADATA_VERSION: int = 6 # as of 10/16/2021
HUB_REPOSITORY_NAME: str = "ydhuang28/covid19-forecast-hub"
VALIDATION_REPOSITORY_ROOT_ONDISK: pathlib.Path = (
    pathlib.Path(__file__)/".."
).resolve()
FORECASTS_DIRECTORY: pathlib.Path = pathlib.Path("./forecasts").resolve()
GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME: str = "GH_TOKEN"

# Filename regex patterns used in code below
# Key name indicate the type of files whose filenames the corresponding rege
# (value) matches on
FILENAME_PATTERNS: dict[PullRequestFileType, re.Pattern] = {
    PullRequestFileType.FORECAST:
        re.compile(r"^data-processed/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv$"),
    PullRequestFileType.METADATA:
        re.compile(r"^data-processed/(.+)/metadata-\1\.txt$"),
    PullRequestFileType.OTHER_FS:
        re.compile(r"^data-processed/(.+)\.(csv|txt)$"),
}

# True/False indicating whether the script is run in a CI environment or not
# The "CI" system environment variable is always set to "true" for GitHub
# Actions: https://docs.github.com/en/actions/reference/environment-variables#default-environment-variables
IS_GITHUB_ACTIONS: bool = os.environ.get("GITHUB_ACTIONS") == "true"

# Logging
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

    # make new validation run
    validation_run = ValidationRun(steps)

    # add initial values to store
    validation_run.store.update({
        "VALIDATIONS_VERSION": VALIDATIONS_VERSION,
        "HUB_REPOSITORY_NAME": HUB_REPOSITORY_NAME,
        "FORECASTS_DIRECTORY": FORECASTS_DIRECTORY,
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