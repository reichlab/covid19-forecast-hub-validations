# external dep.'s
import json
import re
import os
import sys
from typing import Iterable, Optional, Tuple, Union
import urllib.request
import glob
from github import Github
from github.File import File
from github.Label import Label
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.Repository import Repository
import logging
import logging.config

# internal dep.'s
from validation_fns.metadata import check_for_metadata
from validation_fns.forecast_date import filename_match_forecast_date
from test_formatting import forecast_check, print_output_errors
from model_utils import *
from files import FileType

# --- configurations ---

# Current validation version
VALIDATIONS_VERSION: int = 4

# Name of hub repository
HUB_REPOSITORY_NAME: str = "reichlab/covid19-forecast-hub"

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
) -> Tuple[Tuple[bool, list[Label]], Tuple[bool, list[str]]]:
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
    Tuple[list[Label], list[str]],
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
) -> Tuple[bool, dict[FileType, list[File]]]:
    """Filters a list of filenames into corresponding file types.

    Uses match_file() to match File to FileType.

    Args:
        files: List of PyGithub File objects.

    Returns:
        A dictionary keyed by the type of file and contains a list of Files
        of that type as value.
    """
    filtered_files: dict[FileType, list[File]] = {
        file_type: [] for file_type in FileType
    }
    for file in files:
        file_types: list[FileType] = match_file(file, patterns)
        for file_type in file_types:
            filtered_files[file_type].append(file)
    
    return filtered_files

def is_forecast_submission(
    filtered_files: dict[FileType, list(File)]
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

    return (len(filtered_files[FileType.FORECAST]) > 0 or
            len(filtered_files[FileType.METADATA]) > 0 or
            len(filtered_files[FileType.OTHER_FS]) > 0)


def check_file_locations(
    filtered_files: dict[FileType, list(File)],
    all_labels: dict[str, list(Label)],
    *, # forces latter parameters to be keyword-only arguments
    labels_to_apply: Optional[list[Label]] = None,
    comments_to_apply: Optional[list[str]] = None
) -> Optional[Union[
    Tuple[list[Label], list[str]],
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
        labels_to_apply.append(all_labels['other-files-updated'])

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
        labels_to_apply.append(all_labels['metadata-change'])

    return return_labels_comments(
        is_labels_passed_in, is_comments_passed_in,
        labels_to_apply, comments_to_apply
    )

def check_modified_forecasts(
    filtered_files: dict[FileType, list(File)],
    repository: Repository,
    all_labels: dict[str, list(Label)],
    *, # forces latter parameters to be keyword-only arguments
    labels_to_apply: Optional[list[Label]] = None,
    comments_to_apply: Optional[list[str]] = None
) -> Optional[Union[
    Tuple[list[Label], list[str]],
    list[Label],
    list[str]
]]:
    check_results = check_labels_comments(labels_to_apply, comments_to_apply)
    is_labels_passed_in, labels_to_apply = check_results[0]
    is_comments_passed_in, comments_to_apply = check_results[1]

    changed_forecasts = False
    for f in filtered_files[FileType.FORECAST]:
        # GitHub PR file statuses: unofficial, nothing official yet as of 9-4-21
        # "added", "modified", "renamed", "removed"
        # https://stackoverflow.com/questions/10804476/what-are-the-status-types-for-files-in-the-github-api-v3
        # https://github.com/jitterbit/get-changed-files/commit/cfe8ad4269ed4d2edb7f4e39682a649f6675bf89#diff-4fab5baaca5c14d2de62d8d2fceef376ddddcc8e9509d86cfa5643f51b89ce3dR5
        if f.status == "modified" or f.status == "removed":
            # If file is modified, fetch the original one and save it to the forecasts_master directory
            get_model_master(repository, filename=f.filename)
            changed_forecasts = True

    if changed_forecasts:
        # Add the `forecast-updated` label when there are deletions in the forecast file
        labels_to_apply.append(all_labels['forecast-updated'])
        comments_to_apply.append(
            "Your submission seem to have updated/deleted some forecasts. "
            "Could you provide a reason for the updation/deletion and confirm "
            "that any updated forecasts only used data that were available at "
            "the time the original forecasts were made?")

    return return_labels_comments(
        is_labels_passed_in, is_comments_passed_in,
        labels_to_apply, comments_to_apply
    )

def validate() -> None:
    """Entry point and main body of validations script.
    """

    # 0. Preamble
    logger.info("Running validations version %s", VALIDATIONS_VERSION)
    logger.info("GitHub Actions information:")
    logger.info(
        "GitHub Actions event name: %s",
        os.environ.get("GITHUB_EVENT_NAME")
    )

    # 1. Connect to GitHub, get repository
    logger.info("Connecting to GitHub and retrieving repository...")

    github: Github = get_github_object(get_github_token())
    repository: Repository = get_repository(github)
    possible_labels: dict[str, Label] = get_labels(repository)

    logger.info("Repository succesfully retrieved")
    logger.info("Github repository: %s", repository.name)

    # 2. Get pull request number using event payload from GitHub Actions
    event: dict = json.load(open(os.environ.get('GITHUB_EVENT_PATH')))
    pull_request_number: str = event['number']
    pull_request: PullRequest = repository.get_pull(pull_request_number)

    logger.info("Using PR number: %s", pull_request_number)

    # 3. Fetch all files changed in this PR and split all files into
    #    valid forecasts and other files
    logger.info("Filtering PR files by location...")

    filtered_files: dict[FileType, list(File)] = filter_files(
        pull_request.get_files()
    )

    # 4. Decide whether this PR is a forecast submission or not
    if not is_forecast_submission(filtered_files):
        logger.info(
            "PR does not contain files that can be interpreted "
            "as part of a forecast submission; validations skipped."
        )
        return

    # 5. Check PR file locations and assign appropriate labels and
    #    make appropriate comments
    labels, comments = check_file_locations(filtered_files, possible_labels)

    # 6. Check if a forecast file is modified
    check_modified_forecasts(
        filtered_files,
        repository,
        possible_labels,
        labels_to_apply=labels,
        comments_to_apply=comments
    )

    # fetch all model directories in the data folder. Used to validate if this is a new submission
    models = get_models(repository)

    # Download all forecasts
    # create a forecasts directory
    os.makedirs('forecasts', exist_ok=True)

    # Download all forecasts changed in the PR into the forecasts folder
    for f in forecasts:
        urllib.request.urlretrieve(f.raw_url, f"forecasts/{f.filename.split('/')[-1]}")

    # Download all metadata files changed in the PR into the forecasts folder
    for f in metadatas:
        urllib.request.urlretrieve(f.raw_url, f"forecasts/{f.filename.split('/')[-1]}")

    # Run validations on each of these files
    errors = {}
    is_forecast_date_mismatch = False
    for file in glob.glob("forecasts/*.csv"):
        error_file = forecast_check(file)

        # extract just the filename and remove the path.
        f_name = os.path.basename(file)
        if len(error_file) > 0:
            errors[os.path.basename(file)] = error_file

        # Check whether the `model_abbr`  directory is present in the `data-processed` folder.
        # This is a test to check if this submission is a new submission or not
        model = '-'.join(f_name.split('.')[0].split('-')[-2:])  # extract model_abbr from the filename
        if model not in models:
            if not local:
                labels.append('new-team-submission')
            if not os.path.isfile(f"forecasts/metadata-{model}.txt"):
                error_str = "This seems to be a new submission and you have not included a metadata file."
                if len(error_file) > 0:
                    errors[f_name].append(error_str)
                else:
                    errors[f_name] = [error_str]

        # Check for implicit and explicit retractions
        # `forecasts_master` is a directory with the older version of the forecast (if present).
        if os.path.isfile(f"forecasts_master/{f_name}"):
            with open(f"forecasts_master/{f_name}", 'r') as f:
                print("Checking old forecast for any retractions")
                compare_result = compare_forecasts(old=f, new=open(file, 'r'))
                if compare_result['invalid'] and not local:
                    error_msg = compare_result['error']
                    # if there were no previous errors
                    if len(error_file) == 0:
                        errors[os.path.basename(file)] = [compare_result['error']]
                    else:
                        errors[os.path.basename(file)].append(compare_result['error'])
                if compare_result['implicit-retraction'] and not local:
                    labels.append('forecast-implicit-retractions')
                    retract_error = f"The forecast {os.path.basename(file)} has an invalid implicit retraction. Please review the retraction rules for a forecast in the wiki here - https://github.com/reichlab/covid19-forecast-hub/wiki/Forecast-Checks"
                    # throw an error now with Zoltar 4
                    if len(error_file) == 0:
                        errors[os.path.basename(file)] = [retract_error]
                    else:
                        errors[os.path.basename(file)].append(retract_error)
                # explicit retractions
                if compare_result['retraction'] and not local:
                    labels.append('retractions')

        # Check for the forecast date column check is +-1 day from the current date the PR build is running
        is_forecast_date_mismatch, err_message = filename_match_forecast_date(file)
        if is_forecast_date_mismatch:
            comment += err_message

    # Check for metadata file validation
    FILEPATH_META = "forecasts/"
    is_meta_error, meta_err_output = check_for_metadata(filepath=FILEPATH_META)

    if len(errors) > 0:
        comment += "\n\n Your submission has some validation errors. Please check the logs of the build under the \"Checks\" tab to get more details about the error. "
        print_output_errors(errors, prefix='data')

    if is_meta_error:
        comment += "\n\n Your submission has some metadata validation errors. Please check the logs of the build under the \"Checks\" tab to get more details about the error. "
        print_output_errors(meta_err_output, prefix="metadata")

    # add the consolidated comment to the PR
    if comment != '' and not local:
        pull_request.create_issue_comment(comment)

    # Check if PR could be merged automatically
    # Logic - The PR is set to automatically merge if ALL the following conditions are TRUE: 
    #  - If there are no comments added to PR
    #  - If it is not run locally
    #  - If there are not metadata errors
    #  - If there were no validation errors
    #  - If there were any other files updated which includes: 
    #      - any errorneously named forecast file in data-processed folder
    #      - any changes/additions on a metadata file. 
    #  - There is ONLY 1 valid forecast file added that has passed the validations.
    #    That means, there was atleast one valid forecast file (that also passed the validations) added to the PR.

    if comment == '' and not local and not is_meta_error and len(errors) == 0 and (
            len(metadatas) + len(other_files)) == 0 and len(forecasts_err) == len(forecasts) and len(
            forecasts) == 1:
        print(f"Auto merging PR {pr_num if pr_num else -1}")
        labels.append('automerge')

    if pull_request is not None:
        # set labels: labeler labels + validation labels
        labels_to_set = labels + list(filter(lambda l: l.name in {'data-submission', 'viz', 'code'}, pull_request.labels))
        if len(labels_to_set) > 0:
            pull_request.set_labels(*labels_to_set)

    print(f"Using validations version {VALIDATIONS_VERSION}")
    # fail validations build if any error occurs.
    if is_meta_error or len(errors) > 0 or is_forecast_date_mismatch:
        sys.exit("\n ERRORS FOUND EXITING BUILD...")

if __name__ == '__main__':
    if IS_GITHUB_ACTIONS:
        validate()
    else:
        # TODO: add local version
        pass