# external dependencies
from typing import Any
from github import Github
from github.File import File
from github.PullRequest import PullRequest
from github.Repository import Repository
import json
import logging
import os

# internal dependencies
from forecast_validation.files import FileType
from forecast_validation.utils import (
    filter_files,
    is_forecast_submission
)
from forecast_validation.validation import ValidationStepResult


logger = logging.getLogger("hub-validations")

def establish_github_connection(store: dict[str, Any]) -> ValidationStepResult:
    """
    Establishes the connection to GitHub.

    Returns:
        A ValidationStepResult object with the Github object in the to_store
        dictionary.
    """
    """Returns the GitHub PAT stored as a environment variable.

    If the name of the environment variable storing the GitHub PAT is not given,
    then it will default to searching for one named "GH_TOKEN".

    Args:
        github_token_envvar_name: Optional; name of the environment variable
          that stores the GitHub PAT. Defaults to "GH_TOKEN".

    Returns:
        The stored GitHub PAT, None if not found.
    """
    """Returns a PyGithub Github object.
    
    Once created, require a network connection for subsequent calls.

    Args:
        token: Optional; GitHub PAT. If provided can help rate-limiting
          be less limiting. See https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting
          for more details.

    Returns:
        A PyGithub Github object that can be used to make GitHub REST API calls.
    """
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
    pull_request: PullRequest = store["pull_request"]

    filtered_files: dict[FileType, list(File)] = filter_files(
        pull_request.get_files(),
        store["FILENAME_PATTERNS"]
    )

    # Decide whether this PR is a forecast submission or not
    if not is_forecast_submission(filtered_files):
        logger.info(
            "PR does not contain files that can be interpreted "
            "as part of a forecast submission; validations skipped."
        )
        return ValidationStepResult(
            success=True,
            skip_steps_after=True
        )
    else:
        logger.info(
            "PR can be interpreted as a forecast submission, "
            "proceeding with validations."
        )
    
    return ValidationStepResult(
        success=True,
        to_store={"filtered_files": filtered_files}
    )

