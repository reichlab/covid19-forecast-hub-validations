from typing import Optional
from github import Github
import os

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