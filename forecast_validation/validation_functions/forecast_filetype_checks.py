import logging
from typing import Any, Optional, Union
from github.File import File
from github.Label import Label
from github.Repository import Repository
import os.path

from yaml import scan

from forecast_validation.files import FileType
from forecast_validation.validation import ValidationStepResult
from forecast_validation.model_utils import get_model_master

logger = logging.getLogger("hub-validations")

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

    logger.info("Checking if the PR is adding to/updating multiple models...")

    comments = []
    filtered_files: dict[FileType, list[File]] = store["filtered_files"]

    names: set[str] = set()
    if FileType.FORECAST in filtered_files:
        for file in filtered_files[FileType.FORECAST]:
            names.add("-".join(os.path.basename(file.filename).split("-")[-2:]))
    
    if FileType.METADATA in filtered_files:
        for file in filtered_files[FileType.METADATA]:
            names.add("-".join(os.path.basename(file.filename).split("-")[-2:]))
    if len(names) > 0:
        updated_models = ", ".join(names)
        logger.info(
            "⚠️ PR is adding to/updating multiple models: %s",
            updated_models
        )
        comments.append(
            "⚠️ You are adding/updating multiple models' files. Could you "
            "provide a reason for this? If this is unintentional, please check "
            "to make sure to put your files are in the appropriate folder, "
            "and update the PR when you have done that. If you do mean to "
            "update multiple models, we will review the PR manually.\n"
            f"Models that are being updated: {updated_models}"
        )
    else:
        logger.info("✔️ PR is not adding to/updating multiple models")

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
    success: bool = True
    filtered_files: dict[FileType, list[File]] = store["filtered_files"]
    all_labels: dict[str, Label] = store["possible_labels"]
    labels: set[Label] = set()
    comments: list[str] = []

    logger.info(
        "Checking if the PR is updating outside the data-processed/ folder..."
    )
    if FileType.OTHER_NONFS in filtered_files:
        logger.info("⚠️ PR is updating outside the data-processed/ folder.")
        comments.append(
            "⚠️ PR contains file changes that are outside the "
            "`data-processed/` folder."
        )
        labels.add(all_labels["other-files-updated"])
    else:
        logger.info("✔️ PR is not updating outside the data-processed/ folder.")

    logger.info("Checking if the PR contains misplaced CSVs...")
    if (FileType.FORECAST not in filtered_files and
        FileType.OTHER_FS in filtered_files):
        success = False
        logger.info("❌ PR contains misplaced CSVs.")
        comments.append(
            "❌ You have placed forecast CSV(s)/text files in an incorrect "
            "location. Currently, your PR contains CSV(s) and/or text files "
            "that are directly in the `data_processed/` folder and not in your "
            "team's subfolder. Please move your files to the appropriate "
            "location.\n\n"
            "We will still check the misplaced CSV(s) for you, so that you can "
            "be sure that the CSVs are correct, or correct any errors if not."
        )
    else:
        logger.info("✔️ PR does not contain misplaced forecasts.")

    logger.info("Checking if the PR contains metadata updates...")
    if FileType.METADATA in filtered_files:
        logger.info("💡 PR contains metadata updates.")
        comments.append("💡 PR contains metadata file changes.")
        labels.add(all_labels["metadata-change"])

    return ValidationStepResult(
        success=success,
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

    logger.info("Checking if the PR contains updates to existing forecasts...")

    forecasts = filtered_files.get(FileType.FORECAST, [])
    changed_forecasts: bool = False
    for f in forecasts:
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
        logger.info("💡 PR contains updates to existing forecasts.")
        labels.add(all_labels["forecast-updated"])
        comments.append(
            "💡 Your submission seem to have updated/deleted some forecasts. "
            "Could you provide a reason for the updation/deletion and confirm "
            "that any updated forecasts only used data that were available at "
            "the time the original forecasts were made?"
        )
    else:
        logger.info("PR does not contain forecast updates.")

    return ValidationStepResult(
        success=True,
        labels=labels,
        comments=comments
    )
