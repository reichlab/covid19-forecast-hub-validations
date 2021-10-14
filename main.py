# external dep.'s
import logging
import logging.config
import os
import os.path
import pathlib
import re

# internal dep.'s
from forecast_validation.validation import *
from forecast_validation.validation_functions.github_connection import (
    establish_github_connection,
    extract_pull_request
)
from forecast_validation.model_utils import *
from forecast_validation.files import FileType

# --- configurations ---

# Current validation version
VALIDATIONS_VERSION: int = 4

# Name of hub repository
HUB_REPOSITORY_NAME: str = "ydhuang28/covid19-forecast-hub"

# Name of directory to create for forecasts
FORECASTS_DIRECTORY: pathlib.Path = pathlib.Path("forecasts")

# Filename regex patterns used in code below
# Key name indicate the type of files whose filenames the corresponding rege
# (value) matches on
FILENAME_PATTERNS: dict[FileType, re.Pattern] = {
    FileType.FORECAST:
        re.compile(r"^data-processed/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv$"),
    FileType.METADATA: re.compile(r"^data-processed/(.+)/metadata-\1\.txt$"),
    FileType.OTHER_FS: re.compile(r"^data-processed/(.+)\.(csv|txt)$"),
}

# True/False indicating whether the script is run in a CI environment or not
# The "CI" system environment variable is always set to "true" for GitHub
# Actions: https://docs.github.com/en/actions/reference/environment-variables#default-environment-variables
IS_GITHUB_ACTIONS: bool = os.environ.get("GITHUB_ACTIONS") == "true"

GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME = "GH_TOKEN"

# Logging
logging.config.fileConfig('logging.conf')

# --- configurations end ---

def setup_validation_run_for_pull_request() -> ValidationRun:
    
    steps = []

    # Connect to GitHub
    steps.append(ValidationStep(establish_github_connection))

    # Extract PR
    steps.append(ValidationStep(extract_pull_request))
    
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

def validate_from_pull_request():
    setup_validation_run_for_pull_request().run()
    
if __name__ == '__main__':
    print("---------- here ----------")
    if IS_GITHUB_ACTIONS:
        validate_from_pull_request()
        print("****************** success! ******************")
    else:
        # TODO: add local version
        pass