from typing import Any
from github.File import File
from github.Label import Label
import datetime
import logging
import os
import pandas as pd
import pathlib
import pytz
import zoltpy.covid19

from forecast_validation import (
    ParseDateError, PullRequestFileType, RepositoryRelativeFilePath
)
from forecast_validation.checks.forecast_file_content import (
    check_date_format,
    validate_forecast_values
)
from forecast_validation.utilities.github import get_existing_models
from forecast_validation.utilities.misc import extract_model_name
from forecast_validation.validation import ValidationStepResult

logger = logging.getLogger("hub-validations")

def get_all_forecast_filepaths(
    store: dict[str, Any]
) -> ValidationStepResult:
    directory: pathlib.Path = store["PULL_REQUEST_DIRECTORY_ROOT"]
    return ValidationStepResult(
        success=True,
        forecast_files={
            RepositoryRelativeFilePath(fp) for fp in directory.glob("**/*.csv")
        }
    )

def validate_forecast_files(
    store: dict[str, Any],
    files: list[os.PathLike]
) -> ValidationStepResult:
    success: bool = True
    errors: dict[os.PathLike, list[str]] = {}
    correctly_formatted_files: set[os.PathLike] = set()
    population_dataframe_path: pathlib.Path = store["POPULATION_DATAFRAME_PATH"]

    logger.info("Checking forecast formats and values...")

    for file in files:
        logger.info("  Checking forecast format for %s", file)
        file_result = zoltpy.covid19.validate_quantile_csv_file(
            file, silent=True
        )
        if file_result == "no errors":
            logger.info("    %s format validated", file)
            correctly_formatted_files.add(file)
        else:
            file_result = [
                f"Error when validating format: " + e
                for e in file_result
            ]
            success = False
            error_list = errors.get(file, [])
            error_list.extend(file_result)
            errors[file] = error_list
            for error in file_result:
                logger.error("    " + error)

    for file in files:
        logger.info("  Checking forecast values for %s", file)
        if file not in correctly_formatted_files:
            error_message = (
                f"Error when validating forecast values: "
                "skipped due to incorrect file format "
            )
            logger.error("    " + error_message)
            success = False
            error_list = errors.get(file, [])
            error_list.append(error_message)
            errors[file] = error_list
        else:
            file_result = validate_forecast_values(
                file, population_dataframe_path
            )
            if file_result is not None:
                error_message = (
                    f"Error when validating forecast values: "
                    f"{file_result}"
                )
                logger.error("    " + error_message)
                success = False
                error_list = errors.get(file, [])
                error_list.append(error_message)
                errors[file] = error_list
            else:
                logger.info("    %s forecast value sanity-checked", file)

    return ValidationStepResult(
        success=success,
        file_errors=errors
    )

def filename_match_forecast_date_check(
    store: dict[str, Any],
    files: set[os.PathLike]
) -> ValidationStepResult:

    forecast_date_column_name: str = "forecast_date"
    success: bool = True
    errors: dict[os.PathLike, list[str]] = {}
    comments: list[str] = []

    for filepath in files:
        basename: str = os.path.basename(filepath)
        
        logger.info("Checking dates in forecast file %s...", basename)

        # read only the forecast date column to save space
        try:
            df = pd.read_csv(filepath, usecols=[forecast_date_column_name])
        except ValueError:
            logger.error(
                "❌ Forecast file %s is missing the %s column",
                basename, forecast_date_column_name
            )
            return ValidationStepResult(
                success=False,
                file_errors={filepath: [(
                    f"Forecast files must have a column named "
                    f"{forecast_date_column_name} that contains the forecast "
                    "date of the file."
                )]}
            )
        
        forecast_dates: set(datetime.date) = set()
        for date_object in df['forecast_date']:
            date_str = str(date_object)
            try:
                check_date_format(date_str)
            except ParseDateError as pde:
                error_message = (
                    f"column {forecast_date_column_name} contains dates "
                    "that are not in the YYYY-MM-DD format; specifically, "
                    f"{pde.args[0]}"
                )
                logger.error("❌ " + error_message)
                success = False
                error_list = errors.get(filepath, [])
                error_list.append(error_message)
                errors[filepath] = error_list

            try:
                date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as ve:
                error_message = (
                    f"column {forecast_date_column_name} contains dates "
                    f"that are not parseable; specifically, {ve.args[0]}"
                )
                logger.error(error_message)
                success = False
                error_list = errors.get(filepath, [])
                error_list.append(error_message)
                errors[filepath] = error_list
                
            forecast_dates.add(date)

        # extract date from filename
        try:
            file_forecast_date = datetime.datetime.strptime(
                os.path.basename(basename)[:10], "%Y-%m-%d"
            ).date()
        except ValueError as ve:
            error_message = (
                f"filename contains dates "
                f"that are not parseable; specifically, {ve.args[0]}"
            )
            logger.error("❌ " + error_message)
            success = False
            error_list = errors.get(filepath, [])
            error_list.append(error_message)
            errors[filepath] = error_list

        # filter all possible forecast dates into a set for unique check
        forecast_dates = {
            datetime.datetime.strptime(str(d), "%Y-%m-%d").date()
            for d in df['forecast_date']
        }

        # forecast date must be unique in CSV
        if len(forecast_dates) > 1:
            logger.error(
                "❌ Forecast date in the %s column is not unique",
                forecast_date_column_name
            )
            forecast_dates_str = ", ".join([
                datetime.datetime.strftime(d, "%Y-%m-%d")
                    for d in forecast_dates
            ])
            success = False
            error_list = errors.get(filepath, [])
            error_list.append((
                f"Forecast file contains multiple forecast dates: "
                f"{forecast_dates_str}. There must only be one unique "
                "forecast date in one forecast file."
            ))
            errors[filepath] = error_list
        
        # forecast dates must match
        while len(forecast_dates) > 0:
            forecast_date = forecast_dates.pop()
            if (file_forecast_date != forecast_date):
                logger.error(
                    "❌ Forecast dates do not match: %s vs %s",
                    str(file_forecast_date),
                    str(forecast_date)
                )
                success = False
                error_list = errors.get(filepath, [])
                error_list.append((
                    f"date in filename does not match date in "
                    f"`forecast_date` column: {file_forecast_date} vs "
                    f"{forecast_date}."
                ))
                errors[filepath] = error_list
        
            # forecast dates must be <1day within each other
            today = datetime.datetime.now(pytz.timezone('US/Eastern')).date()
            if abs(file_forecast_date - today) > datetime.timedelta(days=1):
                comments.append((
                    f"⚠️ Warning: The forecast file {filepath} is not made "
                    f"today. date of the forecast - {file_forecast_date}, "
                    f"today - {today}."
                ))
                logger.warning(
                    "Forecast file %s is made more than 1 day ago.",
                    basename
                )

    if success:
        logger.info("Forecast date validation successful.")
    
    return ValidationStepResult(
        success=success,
        comments=comments,
        file_errors=errors
    )

def check_new_model(
    store: dict[str, Any],
    files: set[os.PathLike]
) -> ValidationStepResult:

    success: bool = True
    labels: set[Label] = set()
    errors: dict[os.PathLike, list[str]] = {}

    all_labels: dict[str, Label] = store["possible_labels"]
    pull_request_directory_root: pathlib.Path = (
        store["PULL_REQUEST_DIRECTORY_ROOT"]
    )
    filtered_files: dict[PullRequestFileType, list[File]] = (
        store["filtered_files"]
    )
    metadata_files: list[File] = filtered_files.get(
        PullRequestFileType.METADATA, []
    )
    existing_models: list[str] = store["model_names"]

    models_in_pull_request = set()
    model_to_file: dict[str, os.PathLike] = {}
    for file in files:
        filepath = pathlib.Path(file)
        model = extract_model_name(filepath)
        models_in_pull_request.add(model)
        model_to_file[file] = model

    models_with_metadata_in_pull_request = set()
    for metadata_file in metadata_files:
        metadata_file_path = RepositoryRelativeFilePath(
            pull_request_directory_root/pathlib.Path(metadata_file.filename)
        )
        if metadata_file_path.exists():
            model = extract_model_name(metadata_file.filename)
            models_with_metadata_in_pull_request.add(model)

    # read all binary operators below as set operations
    if not models_in_pull_request <= existing_models:
        labels.add(all_labels["new-team-submission"])
        new_models = models_in_pull_request - existing_models
        if not new_models <= models_with_metadata_in_pull_request:
            new_models_without_metadata = (
                new_models - models_with_metadata_in_pull_request
            )

            success = False
            for model in new_models_without_metadata:
                logger.error(
                    "❌ New model without in-folder metadata file detected: %s",
                    model
                )
                errors[model_to_file[model]] = [(
                    f"Looks like you are submitting a new model ({model}), but "
                    "you have not submitted a new metadata file along with it "
                    "in the same team-model folder. Please update your pull "
                    "request to contain a metadata file for the model in the "
                    "same team-model folder that also contains the forecast "
                    "files."
                )]


    return ValidationStepResult(
        success=success,
        labels=labels,
        file_errors=errors
    )
