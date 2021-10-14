# external dep.'s
from typing import Iterable, Optional, Tuple, Union
from github import Github
from github.File import File
from github.Label import Label
from github.PullRequest import PullRequest
from github.Repository import Repository
import itertools
import json
import logging
import logging.config
import os
import os.path
import pathlib
import re
import sys
import urllib.request

# internal dep.'s
from forecast_validation.validation import *
from forecast_validation.validation_functions.metadata import check_for_metadata
from forecast_validation.validation_functions.forecast_date import (
    check_filename_match_forecast_date
)
from forecast_validation.validation_functions.github_connection import (
    establish_github_connection
)
from forecast_validation.test_formatting import forecast_check, print_output_errors
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

def check_labels_comments(
    labels: Optional[list[Label]],
    comments: Optional[list[str]]
) -> tuple[Union[
    tuple[Union[bool, list[Label]]],
    tuple[Union[bool, list[str]]]
]]:
    """Helper function to check labels' and comments' initialization.

    Makes new lists if one or both lists are not initialized.

    Args:
        labels: Can be None, or a list of existing labels
        comments: Can be None, or a list of existing comments

    Returns:
        New lists for labels and/or comments if either or both is None,
        coupled with a boolean to show whether they were passed in with
        existing lists.
    """
    if labels is not None and comments is not None:
        return ((True, labels), (True, comments))
    elif labels is not None:
        return ((True, labels), (False, []))
    elif comments is not None:
        return ((False, []), (True, comments))
    else:
        return ((False, []), (False, []))

def return_labels_comments(
    is_labels_passed_in: bool,
    is_comments_passed_in: bool,
    labels: list[Label],
    comments: list[str]
) -> Optional[Union[
    tuple[Union[list[Label], list[str]]],
    list[Label],
    list[str]
]]:
    """Returns appropriate references based on passed-in indicators.

    If `is_labels_passed_in` is True, then `labels` will not be returned (it is
    assumed that in-place modifications are done on the reference); otherwise it
    will be. Similarly, if `is_comments_passed_in` is True, then `comments` will
    not be returned; otherwise, it will be.

    Args:
        is_labels_passed_in: boolean indicating whether to return `labels`.
        is_comments_passed_in: boolean indicating whether to return `comments`.
        labels: potential return value.
        comments: potential return value.

    Returns:
        Either None, `labels`, `comments`, or `(labels, comments)`.
    """
    if not is_labels_passed_in and not is_comments_passed_in:
        return labels, comments
    elif is_labels_passed_in:
        return comments
    elif is_comments_passed_in:
        return labels

def check_multiple_model_names(
    filtered_files: dict[FileType, list[File]],
    all_labels: dict[str, list[Label]],
    *, # forces latter parameters to be keyword-only arguments
    labels_to_apply: Optional[list[Label]] = None,
    comments_to_apply: Optional[list[str]] = None
) -> Optional[set[tuple[str]]]:
    """Extract team and model names from forecast submission files.

    If unable to extract, returns None.

    Args:
        filtered_files: A dictionary containing lists of files mapped to a
          file type; filtered from a forecast submission PR.

    Returns:
        A set of team and model names wrapped in a tuple;
        None if no names could be extracted.
    """
    check_results = check_labels_comments(labels_to_apply, comments_to_apply)
    is_labels_passed_in, labels_to_apply = check_results[0]
    is_comments_passed_in, comments_to_apply = check_results[1]

    names: set[tuple[str, str]] = set()
    if FileType.FORECAST in filtered_files:
        for file in filtered_files[FileType.FORECAST]:
            names.add(tuple(os.path.basename(file.filename).split("-")[-2:]))
    
    if FileType.METADATA in filtered_files:
        for file in filtered_files[FileType.METADATA]:
            names.add(tuple(os.path.basename(file.filename).split("-")[-2:]))
    
    if len(names) > 0:
        # TODO: add new label to hub
        comments_to_apply.append(
            "You are adding/updating multiple models' files. Could you provide "
            "a reason for doing that? If this is unintentional, please check "
            "to make sure that your files are in the appropriate folder."
        )

    return return_labels_comments(
        is_labels_passed_in, is_comments_passed_in,
        labels_to_apply, comments_to_apply
    )

def check_file_locations(
    filtered_files: dict[FileType, list[File]],
    all_labels: dict[str, list[Label]],
    *, # forces latter parameters to be keyword-only arguments
    labels_to_apply: Optional[list[Label]] = None,
    comments_to_apply: Optional[list[str]] = None
) -> Optional[Union[
    tuple[Union[list[Label], list[str]]],
    list[Label],
    list[str]
]]:
    """Checks file locations and returns appropriate labels and comments.

    Args:
        filtered_filenames: a dictionary of FileType to list of filenames.

    Returns:
        A tuple of a list of Label object and a list of comments as strings.
        Uses `labels_to_apply` and `comments_to_apply` if given, and will
        return appropriately.
    """
    check_results = check_labels_comments(labels_to_apply, comments_to_apply)
    is_labels_passed_in, labels_to_apply = check_results[0]
    is_comments_passed_in, comments_to_apply = check_results[1]

    # Non-forecast-submission file changes:
    # changes that are not in data-processed/ folder
    if len(filtered_files[FileType.OTHER_NONFS]) > 0:
        comments_to_apply.append(
            "PR contains file changes that are outside the "
            "`data-processed/` folder."
        )
        labels_to_apply.append(all_labels["other-files-updated"])

    if (len(filtered_files[FileType.FORECAST]) == 0 and
        len(filtered_files[FileType.OTHER_FS]) > 0):
        comments_to_apply.append(
            "You may have placed a forecast CSV in an incorrect location. "
            "Currently, your PR contains CSVs and/or text files that are "
            "directly in the `data_processed/` folder and not in your team's "
            "subfolder. Please move your files to the appropriate location."
        )

    if len(filtered_files[FileType.METADATA]) > 0:
        comments_to_apply.append("PR contains metadata file changes.")
        labels_to_apply.append(all_labels["metadata-change"])

    return return_labels_comments(
        is_labels_passed_in, is_comments_passed_in,
        labels_to_apply, comments_to_apply
    )

def check_modified_forecasts(
    filtered_files: dict[FileType, list[File]],
    repository: Repository,
    all_labels: dict[str, list[Label]],
    *, # forces latter parameters to be keyword-only arguments
    labels_to_apply: Optional[list[Label]] = None,
    comments_to_apply: Optional[list[str]] = None
) -> Optional[Union[
    tuple[Union[list[Label], list[str]]],
    list[Label],
    list[str]
]]:
    """
    
    Args:
        filtered_files: 
        repository:
        all_labels:
        labels_to_apply:
        comments_to_apply:

    Returns:
    
    """
    check_results = check_labels_comments(labels_to_apply, comments_to_apply)
    is_labels_passed_in, labels_to_apply = check_results[0]
    is_comments_passed_in, comments_to_apply = check_results[1]

    changed_forecasts: bool = False
    for f in filtered_files[FileType.FORECAST]:
        # GitHub PR file statuses: unofficial, nothing official yet as of 9-4-21
        # "added", "modified", "renamed", "removed"
        # https://stackoverflow.com/questions/10804476/what-are-the-status-types-for-files-in-the-github-api-v3
        # https://github.com/jitterbit/get-changed-files/commit/cfe8ad4269ed4d2edb7f4e39682a649f6675bf89#diff-4fab5baaca5c14d2de62d8d2fceef376ddddcc8e9509d86cfa5643f51b89ce3dR5
        if f.status == "modified" or f.status == "removed":
            # if file is modified, fetch the original one and
            # save it to the forecasts_master directory
            get_model_master(repository, filename=f.filename)
            changed_forecasts = True

    if changed_forecasts:
        # Add the `forecast-updated` label when there are deletions in the forecast file
        labels_to_apply.append(all_labels["forecast-updated"])
        comments_to_apply.append(
            "Your submission seem to have updated/deleted some forecasts. "
            "Could you provide a reason for the updation/deletion and confirm "
            "that any updated forecasts only used data that were available at "
            "the time the original forecasts were made?"
        )

    return return_labels_comments(
        is_labels_passed_in, is_comments_passed_in,
        labels_to_apply, comments_to_apply
    )

def download_files(
    files: Iterable[File],
    directory: pathlib.Path
) -> None:
    """Downloads files into the given directory.

    Creates the directory if it does not exist.

    Args:
        files:
        directory:
    """
    if not directory.exists():
        os.makedirs(directory, exist_ok=True)
    
    for file in files:
        urllib.request.urlretrieve(
            file.raw_url,
            directory/os.path.basename(file.filename)
        )

def check_new_model(
    file: pathlib.Path,
    existing_models: list[str],
    all_labels: dict[str, list[Label]],
    *, # forces latter parameters to be keyword-only arguments
    labels_to_apply: Optional[list[Label]] = None,
    comments_to_apply: Optional[list[str]] = None
) -> None:

    check_results = check_labels_comments(labels_to_apply, comments_to_apply)
    is_labels_passed_in, labels_to_apply = check_results[0]
    is_comments_passed_in, comments_to_apply = check_results[1]

    model = '-'.join(file.stem.split('-')[-2:])  
    if model not in existing_models:
        labels_to_apply.append(all_labels['new-team-submission'])
        if not os.path.isfile(f"forecasts/metadata-{model}.txt"):
            error_str = (
                "This seems to be a new submission and you have not "
                "included a metadata file."
            )
            if file_path.name in errors:
                errors[file_path.name].append(error_str)
            else:
                errors[file_path.name] = [error_str]

def validate() -> None:
    """Entry point and main body of validations script.
    """

    # Run validations on each of these files
    errors = {}
    is_forecast_date_mismatch = False
    for file_path in FORECASTS_DIRECTORY.glob("*.csv"):

        # zoltpy checks
        file_error = forecast_check(file_path)

        # everything below - hub-specific checks

        # extract just the filename and remove the path.
        if file_error:
            errors[file_path.name] = file_error

        # Check whether the `model_abbr` directory is present in the
        # `data-processed` folder.
        # This is a test to check if this submission is a new submission or not

        # extract model_abbr from the filename
        model = '-'.join(file_path.stem.split('-')[-2:])  
        if model not in models:
            labels.append('new-team-submission')
            if not os.path.isfile(f"forecasts/metadata-{model}.txt"):
                error_str = (
                    "This seems to be a new submission and you have not "
                    "included a metadata file."
                )
                if file_path.name in errors:
                    errors[file_path.name].append(error_str)
                else:
                    errors[file_path.name] = [error_str]

        # Check for implicit and explicit retractions
        # `forecasts_master` is a directory with the older version of the
        # forecast (if present).
        if os.path.isfile(f"forecasts_master/{file_path.name}"):
            with open(f"forecasts_master/{file_path.name}", 'r') as f:
                print("Checking old forecast for any retractions")
                compare_result = compare_forecasts(
                    old=f,
                    new=open(file_path, 'r')
                )
                if compare_result['invalid']:
                    error_msg = compare_result['error']
                    # if there were no previous errors
                    if len(file_error) == 0:
                        errors[file_path.name] = [compare_result['error']]
                    else:
                        errors[file_path.name].append(compare_result['error'])
                if compare_result['implicit-retraction']:
                    labels.append('forecast-implicit-retractions')
                    retract_error = (
                        f"The forecast {file_path.name} has an invalid "
                        "implicit retraction. Please review the retraction "
                        "rules for a forecast in the wiki here - "
                        "https://github.com/reichlab/covid19-forecast-hub/wiki/Forecast-Checks"
                    )
                    # throw an error now with Zoltar 4
                    if len(file_error) == 0:
                        errors[file_path.name] = [retract_error]
                    else:
                        errors[file_path.name].append(retract_error)
                # explicit retractions
                if compare_result['retraction']:
                    labels.append('retractions')

        # Check for the forecast date column check is +-1 day from the current
        # date the PR build is running
        is_forecast_date_mismatch, err_message = \
            check_filename_match_forecast_date(file_path)
        if is_forecast_date_mismatch:
            comments.append(err_message)

    # Check for metadata file validation
    FILEPATH_META = "forecasts/"
    is_meta_error, meta_err_output = check_for_metadata(filepath=FILEPATH_META)

    if len(errors) > 0:
        comments.append(
            "Your submission has some validation errors. Please check the logs "
            "of the build under the \"Checks\" tab to get more details about "
            "the error."
        )
        print_output_errors(errors, prefix='data')

    if is_meta_error:
        comments.append(
            "Your submission has some metadata validation errors. Please check "
            "the logs of the build under the \"Checks\" tab to get more "
            "details about the error. "
        )
        print_output_errors(meta_err_output, prefix="metadata")

    # add the consolidated comment to the PR
    if comments:
        pull_request.create_issue_comment("\n\n".join(comments))

    # Check if PR could be merged automatically
    # Logic - The PR is set to automatically merge
    # if ALL the following conditions are TRUE: 
    #  - If there are no comments added to PR
    #  - If it is not run locally
    #  - If there are not metadata errors
    #  - If there were no validation errors
    #  - If there were any other files updated which includes: 
    #      - any errorneously named forecast file in data-processed folder
    #      - any changes/additions on a metadata file. 
    #  - There is ONLY 1 valid forecast file added that passed the validations.
    #    That means, there was atleast one valid forecast file
    #    (that also passed the validations) added to the PR.

    no_errors: bool = len(errors) == 0
    has_non_csv_or_metadata: bool = (
            len(filtered_files[FileType.METADATA]) +
            len(filtered_files[FileType.OTHER_NONFS])
    ) != 0
    only_one_forecast_csv: bool = len(filtered_files[FileType.FORECAST]) == 1
    all_csvs_in_correct_location: bool = (
        len(filtered_files[FileType.OTHER_FS]) ==
        len(filtered_files[FileType.FORECAST])
    )

    if (comments and
        not is_meta_error and
        no_errors and 
        not has_non_csv_or_metadata and 
        all_csvs_in_correct_location and
        only_one_forecast_csv
    ):
        logger.info("Auto merging PR %s", pull_request_number)
        labels.append(all_labels['automerge'])

    # set labels: labeler labels + validation labels
    labels_to_set = labels + list(filter(
        lambda l: l.name in {'data-submission', 'viz', 'code'},
        pull_request.labels)
    )
    if len(labels_to_set) > 0:
        pull_request.set_labels(*labels_to_set)

    print(f"Using validations version {VALIDATIONS_VERSION}")
    # fail validations build if any error occurs.
    if is_meta_error or len(errors) > 0 or is_forecast_date_mismatch:
        sys.exit("\n ERRORS FOUND EXITING BUILD...")

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
    if IS_GITHUB_ACTIONS:
        validate_from_pull_request()
        print("****************** success! ******************")
    else:
        # TODO: add local version
        pass