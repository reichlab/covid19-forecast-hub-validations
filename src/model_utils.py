from typing import Optional
from github import Github
import github
import os
from github.Repository import Repository
import yaml
import urllib.request
import sys
import pandas as pd


def get_models(
    repository: Repository,
    directory: str = "data-processed"
) -> list[str]:
    """Get all currently existing model names in repository.

    Args:
        repository: A PyGithub Repository object representing the repository
          to query
        directory: A string representing the subfolder in which the models are
          stored

    Returns:
        
    """
    dirs = repository.get_contents(directory)
    models = []
    for model in dirs:
        if model.type == "dir":
            models.append(model.path.split("/")[-1])
    return models


def fetch_url(url: str, path: str) -> str:
    urllib.request.urlretrieve(url, path)
    return path


def get_metadata_for_model(repo, model_abbr, directory="data-processed"):
    """
        return contents of the metadata file as a python dictionary. If not available, return None
    """
    meta = repo.get_contents(f"{directory}/{model_abbr}/metadata-{model_abbr}.txt")
    try:
        return yaml.safe_load(meta.decoded_content)
    except:
        return None


def get_model_master(
    repository: Repository,
    filename: Optional[str] = None,
    model_abbr: Optional[str] = None,
    timezero: Optional[str] = None,
    directory: str = "data-processed",
    target_dir: str = "forecasts_master"
) -> Optional[str]:
    """Retrieve the forecast from master branch of repo. If not present, return None
    """
    try:
        os.makedirs(target_dir, exist_ok=True)
        if filename is None and (model_abbr is not None and timezero is not None):
            filename = f"{directory}/{model_abbr}/{timezero}-{model_abbr}.csv"
        elif filename is None:
            return None
        return fetch_url(f"https://raw.githubusercontent.com/{repository.full_name}/master/{filename}",
                         f"{target_dir}/{filename.split('/')[-1]}")
    except:
        print(f"{filename} : Forecast not present in master")
        raise sys.exc_info()[0]
        return None


def compare_forecasts(old, new):
    """
    Compare the 2 forecasts and returns whether there are any implicit retractions or not
    @type old: Either a file pointer or a path string.
    @type new: Either a file pointer or a path string.

    @return Bool: Whether this update has a retraction or not
    """
    old_df = pd.read_csv(old, index_col=["forecast_date", "target", "target_end_date", "location",
                                         "type", "quantile"])
    new_df = pd.read_csv(new, index_col=["forecast_date", "target", "target_end_date", "location",
                                         "type", "quantile"])

    result = {
        'implicit-retraction': False,
        'retraction':False,
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
            result['error'] = "Forecast has 100% same values updated."
    except KeyError as e:
        print(e)
        # New forecast has some indices that are NOT in old forecast
        result['implicit-retraction'] = True
    else:   
        # check for explicit rectractions
        # check if mismatches positions have NULLs
        if not (comparison).all(axis=None):
            if ((new_vals.notnull()) & (comparison)).any(axis=None):
                result['retraction'] = True
    return result
