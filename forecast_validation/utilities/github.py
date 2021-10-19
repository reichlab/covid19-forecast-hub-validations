from typing import Optional, Iterable
from github.ContentFile import ContentFile
from github.Repository import Repository
import logging
import os
import yaml

from forecast_validation.utilities.misc import fetch_url

logger = logging.getLogger("hub-validations")

def get_existing_models(
    repository: Repository,
    path: str = "data-processed"
) -> set[str]:
    """Get all currently existing model names in repository.

    Args:
        repository: A PyGithub Repository object representing the repository
          to query
        path: A string representing the subfolder in which the models are
          stored

    Returns:
        A set of model names.
    """

    raw_result = repository.get_contents(path)
    directory_items: list[ContentFile] = (
        raw_result if isinstance(raw_result, Iterable) else [raw_result]
    )
    
    models: set[str] = set()
    for item in directory_items:
        if item.type == "dir":
            models.add(os.path.basename(item.path))
    return models

def get_metadata_for_model(
    repo: Repository,
    model_abbr: str,
    directory: str = "data-processed"
) -> Optional[dict]:
    """Retrieves contents of the metadata file as a python dictionary.

    Args:
        repo:
    
    Returns:
        The metadata file's content as a python dictionary; if not available,
        return None
    """
    meta: ContentFile = repo.get_contents(
        f"{directory}/{model_abbr}/metadata-{model_abbr}.txt"
    )
    assert isinstance(meta, ContentFile), meta

    try:
        return yaml.safe_load(meta.decoded_content)
    except:
        return None

def get_existing_model(
    repository: Repository,
    filename: Optional[str] = None,
    model_abbr: Optional[str] = None,
    timezero: Optional[str] = None,
    remote_directory: str = "data-processed",
    local_directory: str = "forecasts_master"
) -> Optional[str]:
    """Retrieve the forecast from master branch of repo.
    
    If not present, return None.
    """
    try:
        os.makedirs(local_directory, exist_ok=True)
        if filename is None and (model_abbr is not None and timezero is not None):
            filename = (
                f"{remote_directory}/{model_abbr}/"
                f"{timezero}-{model_abbr}.csv"
            )
        elif filename is None:
            return None
        return fetch_url(
            (
                "https://raw.githubusercontent.com/"
                f"{repository.full_name}/master/{filename}"
            ),
            f"{local_directory}/{filename.split('/')[-1]}"
        )
    except:
        logger.warning(
            "%s: Forecast does not exist currently?",
            filename
        )
        return None
