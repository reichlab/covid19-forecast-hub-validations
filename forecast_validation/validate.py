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
from validation import *
from validation_functions.metadata import check_for_metadata
from validation_functions.forecast_date import (
    check_filename_match_forecast_date
)
from validation_functions.github_connection import establish_github_connection
from test_formatting import forecast_check, print_output_errors
from model_utils import *
from files import FileType

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

def get_github_token(
    github_token_environment_variable_name: str = "GH_TOKEN"
) -> Optional[str]:
    """Returns the GitHub PAT stored as a environment variable.

    If the name of the environment variable storing the GitHub PAT is not given,
    then it will default to searching for one named "GH_TOKEN".

    Args:
        github_token_envvar_name: Optional; name of the environment variable
          that stores the GitHub PAT. Defaults to "GH_TOKEN".

    Returns:
        The stored GitHub PAT, None if not found.
    """
    return os.environ.get(github_token_environment_variable_name)

def get_github_object(token: Optional[str] = None) -> Github:
    """Returns a PyGithub Github object.
    
    Once created, require a network connection for subsequent calls.

    Args:
        token: Optional; GitHub PAT. If provided can help rate-limiting
          be less limiting. See https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting
          for more details.

    Returns:
        A PyGithub Github object that can be used to make GitHub REST API calls.
    """
    return Github(token) if token is not None else Github()

def get_repository(
    github: Github,
    environment_variable_name: str = "GITHUB_REPOSITORY",
    fallback_repository_name: str = HUB_REPOSITORY_NAME
) -> Repository:
    """Returns the repository object that we will be working on.

    Uses the repository named in the system environment variable
    "GITHUB_REPOSITORY" if it exists. If not, default to the hub repository
    which is named in the configurations above.

    Args:
        github_object: PyGithub Github object used to make the API call to
          retrieve the repository object.
        fallback_repository_name: Optional; a fallback repository name to use
          in case the GITHUB_REPOSITORY environment varialbe is not set.
    
    Returns:
        A PyGithub Repository object representing the repository that we
        will be working on.
    """
    repository_name: str = os.environ.get(environment_variable_name)
    if repository_name is None:
        repository_name = fallback_repository_name
    return github.get_repo(repository_name)

def get_labels(repository: Repository) -> dict[str, Label]:
    """Returns all possible labels in the repository keyed by their names.

    Uses a Repository object and related GitHub REST API queries.

    Args:
        repository: A PyGithub Repository object representing the repository
          to query.
    
    Returns:
        A dictionary keyed by label names and contain PyGithub Label objects
        as values.
    """
    return {l.name: l for l in repository.get_labels()}

def match_file(
    file: File, patterns: dict[FileType, re.Pattern]
) -> list[FileType]:
    """Returns the type of the file given the filename.

    Uses FILENAME_PATTERNS dictionary in the configuration section
    to do the filename-filetype matching.

    Args:
        file: A PyGithub File object representing the file to match.

    Returns:
        A list of all possible file types that the file matched on.
    """
    matched = []
    for filetype in patterns:
        if patterns[filetype].match(file.filename):
            matched.append[filetype]
    if len(matched) == 0:
        matched.append[FileType.OTHER_NONFS]

def filter_files(
    files: Iterable[File],
    patterns: dict[FileType, re.Pattern] = FILENAME_PATTERNS
) -> dict[FileType, list[File]]:
    """Filters a list of filenames into corresponding file types.

    Uses match_file() to match File to FileType.

    Args:
        files: List of PyGithub File objects.

    Returns:
        A dictionary keyed by the type of file and contains a list of Files
        of that type as value.
    """
    filtered_files: dict[FileType, list[File]] = {}
    for file in files:
        file_types: list[FileType] = match_file(file, patterns)
        for file_type in file_types:
            if file_type not in filtered_files:
                filtered_files[file_type] = [file]
            else:
                filtered_files[file_type].append(file)
    
    return filtered_files

def is_forecast_submission(
    filtered_files: dict[FileType, list[File]]
) -> bool:
    """Checks types of files to determine if the PR is a forecast submission.

    There must be at least one file that is not of type `FileType.OTHER_NONFS`.
    To see how file types are determined, check the `FILENAME_PATTERNS`
    dictionary in the configuration section or a similar dictionary passed into
    a preceding call of `filter_files()`.

    Args:
        filtered_files: A dictionary containing lists of PyGithub File objects
          mapped to their type.

    Returns:
        True if the given file dictionary represents a forecast submission PR,
        False if not.
    """

    # TODO: this is really better done by separating the data repository from
    # code that runs on that repository. However, that is a super big change,
    # so more discussion and decision-making is required.

    return (FileType.FORECAST in filtered_files or
            FileType.METADATA in filtered_files or
            FileType.OTHER_FS in filtered_files)

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

    # Preamble
    logger.info("Running validations version %s", VALIDATIONS_VERSION)
    logger.info("Current working directory: %s", os.getcwd())
    logger.info("GitHub Actions information:")
    logger.info(
        "GitHub Actions event name: %s",
        os.environ.get("GITHUB_EVENT_NAME")
    )

    # Connect to GitHub, get repository
    logger.info("Connecting to GitHub and retrieving repository...")

    github: Github = get_github_object(get_github_token())
    repository: Repository = get_repository(github)
    all_labels: dict[str, Label] = get_labels(repository)
 
    logger.info("Repository successfully retrieved")
    logger.info("Github repository: %s", repository.name)

    # Get pull request number using event payload from GitHub Actions
    event: dict = json.load(open(os.environ.get('GITHUB_EVENT_PATH')))
    pull_request_number: str = event['number']
    pull_request: PullRequest = repository.get_pull(pull_request_number)

    logger.info("Using PR number: %s", pull_request_number)

    # Fetch all files changed in this PR and split all files into
    # valid forecasts and other files
    logger.info("Filtering PR files by location...")

    filtered_files: dict[FileType, list(File)] = filter_files(
        pull_request.get_files()
    )

    # Decide whether this PR is a forecast submission or not
    if not is_forecast_submission(filtered_files):
        logger.info(
            "PR does not contain files that can be interpreted "
            "as part of a forecast submission; validations skipped."
        )
        return
    else:
        logger.info(
            "PR can be interpreted as a forecast submission, "
            "proceeding with validations."
        )

    # Check PR file locations
    labels: list[Label]
    comments: list[str]
    labels, comments = check_file_locations(filtered_files, all_labels)

    # Check and see if multiple team-models are updated
    check_multiple_model_names(
        filtered_files,
        all_labels,
        labels_to_apply=labels,
        comments_to_apply=comments
    )

    # Check if forecast files are modified
    check_modified_forecasts(
        filtered_files,
        repository,
        all_labels,
        labels_to_apply=labels,
        comments_to_apply=comments
    )

    # Fetch all current model directories from hub.
    # Used to validate if this is a new submission
    models: dict[str] = get_models(repository)

    # Download all forecasts and metadata files in the PR
    # into the forecasts folder
    download_files(
        itertools.chain(
            filtered_files[FileType.FORECAST],
            filtered_files[FileType.METADATA]
        ),
        FORECASTS_DIRECTORY
    )

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