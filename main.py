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
    establish_github_connection
)
from forecast_validation.model_utils import *
from forecast_validation.files import FileType

# --- configurations ---

# Current validation version
VALIDATIONS_VERSION: int = 4

# Name of hub repository
HUB_REPOSITORY_NAME: str = "reichlab/covid19-forecast-hub"

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
IS_GITHUB_ACTIONS: bool = os.environ.get("GITHUB_ACTIONS") != "true"

# Logging
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('hub-validations')

# --- configurations end ---

def register_validation_steps_for_pull_request() -> ValidationRun:
    
    steps = []

    # Connect to GitHub
    steps.append(ValidationStep(establish_github_connection))
    
    # make new validation run
    validation_run = ValidationRun(steps)
    return validation_run

def validate_from_pull_request():
    validation_run = register_validation_steps_for_pull_request()
    validation_run.run()
    
if __name__ == '__main__':
    print("---------- here ----------")
    print(os.environ)
    if IS_GITHUB_ACTIONS:
        validate_from_pull_request()
        print("****************** success! ******************")
    else:
        # TODO: add local version
        pass