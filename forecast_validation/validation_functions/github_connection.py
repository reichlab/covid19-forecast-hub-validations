# external dependencies
from typing import Any, Optional
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository
import json
import logging
import os

# internal dependencies
from forecast_validation.validation import ValidationStepResult

logger = logging.getLogger('hub-validations')

def establish_github_connection(store: dict[str, Any]) -> ValidationStepResult:
    """
    Establishes the connection to GitHub.

    Returns:
        A ValidationStepResult object with the Github object in the to_store
        dictionary.
    """
    
    logger.info(
        "Running validations version %s",
        store.get(
            "VALIDATION_VERSION",
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
    logger.info("Github repository: %s", repository.name)

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
