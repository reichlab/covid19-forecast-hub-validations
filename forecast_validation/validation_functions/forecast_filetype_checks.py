from typing import Any, Optional, Union
from github.File import File
from github.Label import Label
from github.Repository import Repository
import os.path

from yaml import scan

from forecast_validation.files import FileType
from forecast_validation.validation import ValidationStepResult
from forecast_validation.model_utils import get_model_master

def check_multiple_model_names(store: dict[str, Any]) -> ValidationStepResult:
    """Extract team and model names from forecast submission files.

    If unable to extract, returns None.

    Args:
        filtered_files: A dictionary containing lists of files mapped to a
          file type; filtered from a forecast submission PR.

    Returns:
        A set of team and model names wrapped in a tuple;
        None if no names could be extracted.
    """
    comments = []
    filtered_files: dict[FileType, list[File]] = store["filtered_files"]

    names: set[tuple[str, str]] = set()
    if FileType.FORECAST in filtered_files:
        for file in filtered_files[FileType.FORECAST]:
            names.add(tuple(os.path.basename(file.filename).split("-")[-2:]))
    
    if FileType.METADATA in filtered_files:
        for file in filtered_files[FileType.METADATA]:
            names.add(tuple(os.path.basename(file.filename).split("-")[-2:]))
    if len(names) > 0:
        comments.append(
            "You are adding/updating multiple models' files. Could you provide "
            "a reason for this? If this is unintentional, please check "
            "to make sure to put your files are in the appropriate folder, "
            "and update the PR when you have done that. If you do mean to "
            "update multiple models, we will review the PR manually."
        )

    return ValidationStepResult(
        success=True,
        comments=comments
    )

def check_file_locations(store: dict[str, Any]) -> ValidationStepResult:
    """Checks file locations and returns appropriate labels and comments.

    Args:
        filtered_filenames: a dictionary of FileType to list of filenames.

    Returns:
        A tuple of a list of Label object and a list of comments as strings.
        Uses `labels_to_apply` and `comments_to_apply` if given, and will
        return appropriately.
    """
    filtered_files: dict[FileType, list[File]] = store["filtered_files"]
    all_labels: dict[str, Label] = store["possible_labels"]
    labels: set[Label] = set()
    comments: list[str] = []

    # Non-forecast-submission file changes:
    # changes that are not in data-processed/ folder
    if len(filtered_files[FileType.OTHER_NONFS]) > 0:
        comments.append(
            "PR contains file changes that are outside the "
            "`data-processed/` folder."
        )
        labels.add(all_labels["other-files-updated"])

    if (len(filtered_files[FileType.FORECAST]) == 0 and
        len(filtered_files[FileType.OTHER_FS]) > 0):
        comments.append(
            "You may have placed a forecast CSV in an incorrect location. "
            "Currently, your PR contains CSVs and/or text files that are "
            "directly in the `data_processed/` folder and not in your team's "
            "subfolder. Please move your files to the appropriate location."
        )

    if len(filtered_files[FileType.METADATA]) > 0:
        comments.append("PR contains metadata file changes.")
        labels.add(all_labels["metadata-change"])

    return ValidationStepResult(
        success=True,
        labels=labels,
        comments=comments
    )

def check_modified_forecasts(store: dict[str, Any]) -> ValidationStepResult:
    """
    
    Args:
        filtered_files: 
        repository:
        all_labels:
        labels_to_apply:
        comments_to_apply:

    Returns:
    
    """
    repository: Repository = store["repository"]
    filtered_files: dict[FileType, list[File]] = store["filtered_files"]
    all_labels: dict[str, Label] = store["possible_labels"]
    labels: set[Label] = set()
    comments: list[str] = []

    changed_forecasts: bool = False
    for f in filtered_files[FileType.FORECAST]:
        # GitHub PR file statuses: unofficial, nothing official yet as of 9-4-21
        # "added", "modified", "renamed", "removed"
        # https://stackoverflow.com/questions/10804476/what-are-the-status-types-for-files-in-the-github-api-v3
        # https://github.com/jitterbit/get-changed-files/commit/cfe8ad4269ed4d2edb7f4e39682a649f6675bf89#diff-4fab5baaca5c14d2de62d8d2fceef376ddddcc8e9509d86cfa5643f51b89ce3dR5
        if f.status == "modified" or f.status == "removed":
            # if file is modified, fetch the original one and
            # save it to the forecasts_master directory
            get_model_master(repository, filename=f.filename)
            changed_forecasts = True

    if changed_forecasts:
        # Add the `forecast-updated` label when there are deletions in the forecast file
        labels.add(all_labels["forecast-updated"])
        comments.append(
            "Your submission seem to have updated/deleted some forecasts. "
            "Could you provide a reason for the updation/deletion and confirm "
            "that any updated forecasts only used data that were available at "
            "the time the original forecasts were made?"
        )

    return ValidationStepResult(
        success=True,
        labels=labels,
        comments=comments
    )
