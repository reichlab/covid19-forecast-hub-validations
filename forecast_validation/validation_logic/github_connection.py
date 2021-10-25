# external dependencies
from typing import Any
from github import Github
from github.File import File
from github.Label import Label
from github.PullRequest import PullRequest
from github.Repository import Repository
import itertools
import json
import logging
import os
import os.path
import pathlib
import urllib.request

# internal dependencies
from forecast_validation import (
    PullRequestFileType
)
from forecast_validation.checks.forecast_file_type import (
    filter_files,
    is_forecast_submission
)
from forecast_validation.utilities.github import (
    get_existing_models
)
from forecast_validation.validation import ValidationStepResult

logger = logging.getLogger("hub-validations")

def establish_github_connection(store: dict[str, Any]) -> ValidationStepResult:
    """
    Establishes the connection to GitHub.

    If the name of the environment variable storing the GitHub PAT is not given,
    then it will default to searching for one named "GH_TOKEN". If provided, 
    can help rate-limiting be less stringent. See https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting
    for more details.

    Uses the repository named in the system environment variable
    "GITHUB_REPOSITORY" if it exists. If not, default to the hub repository
    which is named in the configurations (loaded in using the store).

    Returns:
        A ValidationStepResult object with
            * the Github object,
            * the object of the repository from which the pull
                request originated
            * a dictionary of label names to labels that can be applied to the
                pull request.
    """
    
    logger.info(
        "Running validations version %s",
        store.get(
            "VALIDATIONS_VERSION",
            "<missing validation version number>"
        )
    )
    logger.info("Current working directory: %s", os.getcwd())
    logger.info("GitHub Actions information:")
    logger.info(
        "GitHub Actions event name: %s",
        os.environ.get("GITHUB_EVENT_NAME", "<missing GitHub event name>")
    )

    logger.info("Connecting to GitHub and retrieving repository...")

    # initial GitHub connection
    github_PAT: str = os.environ.get(store.get(
        "GITHUB_TOKEN_ENVIRONMENT_VARIABLE_NAME",
        "GH_TOKEN"
    ))
    github: Github = Github(github_PAT) if github_PAT is not None else Github()
    
    # Get specific repository
    repository_name = os.environ.get(
        "GITHUB_REPOSITORY",
        store.get("HUB_REPOSITORY_NAME")
    )
    if repository_name is None:
        raise RuntimeError("FAILURE: could not find GitHub repository")
    repository: Repository = github.get_repo(repository_name)

    # Get list of possible labels to apply to PR
    possible_labels = {l.name: l for l in repository.get_labels()}

    logger.info("Repository successfully retrieved")
    logger.info("Github repository: %s", repository.full_name)

    return ValidationStepResult(
        success=True,
        to_store={
            "github": github,
            "repository": repository,
            "possible_labels": possible_labels
        }
    )

def extract_pull_request(store: dict[str, Any]) -> ValidationStepResult:
    """Extracts the pull request that the validations will be run on.
    """
    repository: Repository = store["repository"]
    with open(os.environ.get("GITHUB_EVENT_PATH")) as event_file:
        event: dict = json.load(event_file)
    pull_request_number: str = event['number']
    pull_request: PullRequest = repository.get_pull(pull_request_number)

    logger.info("Using PR number: %s", pull_request_number)

    return ValidationStepResult(
        success=True,
        to_store={"pull_request": pull_request}
    )

def determine_pull_request_type(store: dict[str, Any]) -> ValidationStepResult:
    """Determines whether the pull request is a forecast submission or not.

    If it decides it is not, then a ValidationStepResult with the
    skip_steps_after flag set to True will be returned, which will cause the
    validation engine to skip the rest of the validation steps.
    """
    pull_request: PullRequest = store["pull_request"]
    all_labels: dict[str, Label] = store["possible_labels"]

    filtered_files: dict[PullRequestFileType, list(File)] = filter_files(
        pull_request.get_files(),
        store["FILENAME_PATTERNS"]
    )
    labels: set[Label] = set()

    logger.info("Determining if PR is a forecast submission...")
    if not is_forecast_submission(filtered_files):
        other_files = filtered_files[PullRequestFileType.OTHER_NONFS]
        for file in other_files:
            labels.add(all_labels["other-files-updated"])
            if file.filename.startswith("code"):
                labels.add(all_labels["code"])
            if os.path.basename(file.filename) == "package.json":
                labels.add(all_labels["dependencies"])
        logger.info(
            "PR does not contain files that can be interpreted "
            "as part of a forecast submission; validations skipped."
        )
        return ValidationStepResult(
            success=True,
            skip_steps_after=True
        )
    else:
        if PullRequestFileType.FORECAST in filtered_files:
            labels.add(all_labels["data-submission"])
        logger.info(
            "PR can be interpreted as a forecast submission, "
            "proceeding with validations."
        )
    
    return ValidationStepResult(
        success=True,
        labels=labels,
        to_store={"filtered_files": filtered_files}
    )

def get_all_models_from_repository(
    store: dict[str, Any]
) -> ValidationStepResult:
    repository: Repository = store["repository"]

    logger.info("Retrieving all existing model names...")

    model_names: set[str] = get_existing_models(repository)

    logger.info("All model names successfully retrieved")

    return ValidationStepResult(
        success=True,
        to_store={
            "model_names": model_names
        }
    )

def download_all_forecast_and_metadata_files(
    store: dict[str, Any]
) -> ValidationStepResult:
    root_directory: pathlib.Path = store["PULL_REQUEST_DIRECTORY_ROOT"]
    filtered_files: dict[PullRequestFileType, list[File]] = (
        store["filtered_files"]
    )

    logger.info("Downloading forecast and metadata files...")

    files = itertools.chain(filtered_files.values())

    if not root_directory.exists():
        os.makedirs(root_directory, exist_ok=True)

    for file in files:
        filepath = pathlib.Path(file.filename)

        parent_directory = (root_directory/filepath.parent).resolve()
        if not parent_directory.exists():
            os.makedirs(parent_directory)

        local_path = (
            root_directory/pathlib.Path(file.filename)
        ).resolve()
        urllib.request.urlretrieve(
            file.raw_url,
            local_path,
        )

    logger.info("Download successful")

    return ValidationStepResult(
        success=True
    )
