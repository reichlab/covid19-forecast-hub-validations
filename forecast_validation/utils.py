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
