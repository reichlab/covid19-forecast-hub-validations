from typing import Optional, Iterable
from github.ContentFile import ContentFile
from github.GithubException import UnknownObjectException
from github.File import File
from github.Repository import Repository
import logging
import os
import pathlib
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

def get_existing_forecast_file(
    repository: Repository,
    model: str,
    file: File,
    local_directory: pathlib.Path,
    remote_data_directory: str = "data_processed",
) -> os.PathLike:
    """Retrieve the forecast from master branch of repo.

    Precondition: assumes that the file/model is already in the master
    branch of the repository.
    
    If not present, return None.
    """
    local_path: pathlib.Path = local_directory/pathlib.Path(file.filename)

    os.makedirs(local_directory, exist_ok=True)
    existing_file: ContentFile = repository.get_contents(
        f"{remote_data_directory}/{model}/{file.filename}"
    )
    assert isinstance(existing_file, ContentFile), existing_file

    return fetch_url(existing_file.download_url, local_path)

