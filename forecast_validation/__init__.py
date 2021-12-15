from typing import Union
import enum
import os
import pathlib
import re

class PullRequestFileType(enum.Enum):
    """Represents different types of files in a PR.
    """
    FORECAST = enum.auto()
    METADATA = enum.auto()
    OTHER_FS = enum.auto()
    OTHER_NONFS = enum.auto()

class FilePathError(BaseException):
    pass

class ParseDateError(BaseException):
    pass

VALIDATIONS_VERSION: int = 4 # as of 10/16/2021
METADATA_VERSION: int = 6 # as of 10/16/2021
"""
REPOSITORY_ROOT_ONDISK: pathlib.Path = (
    pathlib.Path(__file__)/".."/".."
).resolve()
HUB_REPOSITORY_NAME: str = "reichlab/covid19-forecast-hub"
HUB_MIRRORED_DIRECTORY_ROOT: pathlib.Path = (
    (REPOSITORY_ROOT_ONDISK/"hub").resolve()
)
PULL_REQUEST_DIRECTORY_ROOT: pathlib.Path = (
    (REPOSITORY_ROOT_ONDISK/"pull_request").resolve()
)
POPULATION_DATAFRAME_PATH: pathlib.Path = (
    (
        REPOSITORY_ROOT_ONDISK/"forecast_validation"/"static"/"locations.csv"
    ).resolve()
)

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
 """