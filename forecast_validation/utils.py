from typing import Optional, Iterable
from github.ContentFile import ContentFile
from github.File import File
from github.Repository import Repository
import os
import os.path
import pandas as pd
import re
import urllib.request
import yaml

from forecast_validation.files import FileType

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
            matched.append(filetype)
    if len(matched) == 0:
        matched.append[FileType.OTHER_NONFS]

    return matched

def filter_files(
    files: Iterable[File],
    patterns: dict[FileType, re.Pattern]
) -> dict[FileType, list[File]]:
    """Filters a list of filenames into corresponding file types.

    Uses match_file() to match File to FileType.

    Args:
        files: List of PyGithub File objects.

    Returns:
        A dictionary keyed by the type of file and contains a list of Files
        of that type as value.
    """
    filtered_files: dict[FileType, list[File]] = {}
    for file in files:
        file_types: list[FileType] = match_file(file, patterns)
        for file_type in file_types:
            if file_type not in filtered_files:
                filtered_files[file_type] = [file]
            else:
                filtered_files[file_type].append(file)
    
    return filtered_files

def is_forecast_submission(
    filtered_files: dict[FileType, list[File]]
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

    return (FileType.FORECAST in filtered_files or
            FileType.METADATA in filtered_files or
            FileType.OTHER_FS in filtered_files)

def get_models(
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
    # PyGithub (by extension, the GitHub API v3), returns a single non-Iterable
    # file if the path queried is not a directory. This should really be an
    # error, but since we filter by item.type in the following for-loop, the
    # single item will be filtered out anyway, so it is OK.
    raw_result = repository.get_contents(path)
    if not isinstance(raw_result, Iterable):
        directory_items: list[ContentFile] = [raw_result]
    else:
        directory_items: list[ContentFile] = raw_result
    
    models: set[str] = set()
    for item in directory_items:
        if item.type == "dir":
            models.add(os.path.basename(item.path))
    return models

def fetch_url(url: str, path: str) -> str:
    urllib.request.urlretrieve(url, path)
    return path

def get_metadata_for_model(repo, model_abbr, directory="data-processed"):
    """return contents of the metadata file as a python dictionary.
    
    If not available, return None
    """
    meta = repo.get_contents(f"{directory}/{model_abbr}/metadata-{model_abbr}.txt")
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
        print(f"{filename} : Forecast not present in master")
        return None

def compare_forecasts(old, new) -> bool:
    """
    Compare the 2 forecasts and returns whether there are any implicit retractions or not

    Args:
        old: Either a file pointer or a path string.
        new: Either a file pointer or a path string.

    Returns:
        Whether this update has a retraction or not
    """
    columns = [
        "forecast_date",
        "target",
        "target_end_date",
        "location",
        "type",
        "quantile"
    ]
    old_df = pd.read_csv(old, index_col=columns)
    new_df = pd.read_csv(new, index_col=columns)

    result = {
        'implicit-retraction': False,
        'retraction': False,
        'invalid': False,
        'error': None
    }
    # First check if new dataframe has entries for ALL values of old dataframe
    try:
        # Access the indices of old forecast file in the new one
        # TODO: There is definitely a more elegant way to do this!
        new_vals = new_df.loc[old_df.index]
        comparison = (old_df == new_vals)
        if (comparison).all(axis=None):
            result['invalid'] = True
            result['error'] = "Forecast is all duplicate."
    except KeyError as e:
        # print(e)
        # New forecast has some indices that are NOT in old forecast
        result['implicit-retraction'] = True
    else:   
        # check for explicit retractions
        # check if mismatches positions have NULLs
        if not (comparison).all(axis=None):
            if ((new_vals.notnull()) & (comparison)).any(axis=None):
                result['retraction'] = True
    return result

