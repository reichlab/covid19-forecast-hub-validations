# external dependencies
from typing import Any, Optional
from github import Github
import logging
import os

# internal dependencies
from forecast_validation.validation import ValidationStepResult
from forecast_validation.utils import get_github_token, get_github_object
from forecast_validation.validate import VALIDATIONS_VERSION

logger = logging.getLogger('hub-validations')

def establish_github_connection() -> ValidationStepResult:
    """
    Establishes the connection to GitHub.

    Returns:
        A ValidationStepResult object with the Github object in the to_store
        dictionary.
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

    return ValidationStepResult(
        success=True,
        to_store={"github_object": github}
    )
