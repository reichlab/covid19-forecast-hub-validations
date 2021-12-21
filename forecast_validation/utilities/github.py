from typing import Optional, Iterable
from github.ContentFile import ContentFile
from github.GithubException import UnknownObjectException
from github.File import File
from github.Repository import Repository
import base64
import logging
import os
import pathlib
import yaml

from forecast_validation.utilities.misc import fetch_url

logger = logging.getLogger("hub-validations")

def get_existing_models(
    repository: Repository,
    path: str
) -> set[str]:
    """Get all currently existing model names in repository.

    Args:
        repository: A PyGithub Repository object representing the repository
          to query
        path: A string representing the subfolder in which the models are
          stored. eg: "data-processed" and "data-forecasts"

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
    directory: str
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
    file: File,
    local_directory: pathlib.Path,
) -> os.PathLike:
    """Retrieve the forecast from master branch of repo.

    Precondition: assumes that the file/model is already in the master
    branch of the repository.
    
    If not present, return None.
    """
    local_path: pathlib.Path = (
        local_directory/pathlib.Path(file.filename)
    ).resolve()

    os.makedirs(local_path.parent, exist_ok=True)
    
    # https://github.com/PyGithub/PyGithub/issues/661
    blob = get_blob_content(repository, "master", file.filename)
    assert blob.encoding == "base64"

    with open(local_path, "wb") as output_file:
        output_file.write(base64.b64decode(blob.content))

    return local_path

def get_blob_content(
    repository: Repository,
    branch: str,
    path_name: str
):
    # first get the branch reference
    ref = repository.get_git_ref(f'heads/{branch}')
    # then get the tree
    tree = repository.get_git_tree(ref.object.sha, recursive='/' in path_name).tree
    # look for path in tree
    sha = [x.sha for x in tree if x.path == path_name]
    if not sha:
        # well, not found..
        return None
    # we have sha
    return repository.get_git_blob(sha[0])