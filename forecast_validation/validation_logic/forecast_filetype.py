from typing import Any, Optional, Union
from github.File import File
from github.Label import Label
from github.Repository import Repository
import logging
import pathlib
import os

from forecast_validation import PullRequestFileType
from forecast_validation.validation import ValidationStepResult
from forecast_validation.utilities.github import (
    get_existing_model
)

logger = logging.getLogger("hub-validations")

def check_multiple_model_names(store: dict[str, Any]) -> ValidationStepResult:
    """Checks if the PR is updating multiple models.
    """

    logger.info("Checking if the PR is adding to/updating multiple models...")

    comments = []
    filtered_files: dict[PullRequestFileType, list[File]] = (
        store["filtered_files"]
    )

    names: set[str] = set()
    files_to_check: list[File] = (
        filtered_files.get(PullRequestFileType.FORECAST, []) +
        filtered_files.get(PullRequestFileType.METADATA, [])
    )
    for file in files_to_check:
        filepath = pathlib.Path(file.filename)
        names.add("-".join(filepath.stem.split("-")[-2:]))
    if len(names) > 1:
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
    """
    success: bool = True
    filtered_files: dict[PullRequestFileType, list[File]] = (
        store["filtered_files"]
    )
    all_labels: dict[str, Label] = store["possible_labels"]
    labels: set[Label] = set()
    comments: list[str] = []
    errors: dict[os.PathLike, list[str]] = {}

    logger.info(
        "Checking if the PR is updating outside the data-processed/ folder..."
    )
    if PullRequestFileType.OTHER_NONFS in filtered_files:
        logger.info("⚠️ PR is updating outside the data-processed/ folder")
        comments.append(
            "⚠️ PR contains file changes that are outside the "
            "`data-processed/` folder."
        )
        labels.add(all_labels["other-files-updated"])
    else:
        logger.info("✔️ PR is not updating outside the data-processed/ folder")

    logger.info("Checking if the PR contains misplaced CSVs...")
    if (PullRequestFileType.FORECAST not in filtered_files and
        PullRequestFileType.OTHER_FS in filtered_files):
        success = False
        logger.info("❌ PR contains misplaced CSVs.")
        for github_file in filtered_files[PullRequestFileType.OTHER_FS]:
            path = pathlib.Path(github_file.filename)

            errors[path] = [(
                "You have placed forecast CSV(s)/text files in an "
                "incorrect location. Currently, your PR contains CSV(s) "
                "and/or text files that are directly in the "
                "`data_processed/` folder and not in your team's "
                "subfolder. Please move your files to the appropriate "
                "location.\n We will still check the misplaced CSV(s) for "
                "you, so that you can be sure that the CSVs are correct, "
                "or correct any errors if not."
            )]
    else:
        logger.info("✔️ PR does not contain misplaced forecasts")

    logger.info("Checking if the PR contains metadata updates...")
    if PullRequestFileType.METADATA in filtered_files:
        logger.info("💡 PR contains metadata updates")
        comments.append("💡 PR contains metadata file changes.")
        labels.add(all_labels["metadata-change"])

    return ValidationStepResult(
        success=success,
        labels=labels,
        comments=comments,
        errors=errors
    )

def check_modified_forecasts(store: dict[str, Any]) -> ValidationStepResult:
    """Checks if a PR contains updates to existing forecasts.
    """
    repository: Repository = store["repository"]
    filtered_files: dict[PullRequestFileType, list[File]] = (
        store["filtered_files"]
    )
    all_labels: dict[str, Label] = store["possible_labels"]
    labels: set[Label] = set()
    comments: list[str] = []

    logger.info("Checking if the PR contains updates to existing forecasts...")

    forecasts = filtered_files.get(PullRequestFileType.FORECAST, [])
    changed_forecasts: bool = False
    for f in forecasts:
        # GitHub PR file statuses: unofficial, nothing official yet as of 9-4-21
        # "added", "modified", "renamed", "removed"
        # https://stackoverflow.com/questions/10804476/what-are-the-status-types-for-files-in-the-github-api-v3
        # https://github.com/jitterbit/get-changed-files/commit/cfe8ad4269ed4d2edb7f4e39682a649f6675bf89#diff-4fab5baaca5c14d2de62d8d2fceef376ddddcc8e9509d86cfa5643f51b89ce3dR5
        if f.status == "modified" or f.status == "removed":
            # if file is modified, fetch the original one and
            # save it to the forecasts_master directory
            get_existing_model(repository, filename=f.filename)
            changed_forecasts = True

    if changed_forecasts:
        # Add the `forecast-updated` label when there are deletions in the forecast file
        logger.info("💡 PR contains updates to existing forecasts")
        labels.add(all_labels["forecast-updated"])
        comments.append(
            "💡 Your submission seem to have updated/deleted some existing "
            " forecasts. Could you provide a reason for the updation/deletion "
            "and confirm that any updated forecasts only used data that were "
            "available at the time the original forecasts were made?"
        )
    else:
        logger.info("✔️ PR does not contain updates to existing forecasts")

    return ValidationStepResult(
        success=True,
        labels=labels,
        comments=comments
    )
