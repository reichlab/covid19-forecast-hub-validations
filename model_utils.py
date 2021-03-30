from github import Github
import os
import yaml

def get_models(repo, directory="data-processed"):
    """
        fetch all directories inside the data-processed folder. 
        repo: The Github Repository Object
    """
    dirs = repo.get_contents(directory)
    models = []
    for model in dirs:
        if model.type == "dir":
            models.append(model.path.split("/")[-1])


def get_metadata_for_model(repo, model_abbr, directory="data-processed"):
    """
        return contents of the metadata file as a python dictionary. If not available, return None
    """
    meta = repo.get_contents(f"{directory}/{model_abbr}/metadata-{model_abbr}.txt")
    try:
        return yaml.safe_load(meta.decoded_content)
    except:
        return None