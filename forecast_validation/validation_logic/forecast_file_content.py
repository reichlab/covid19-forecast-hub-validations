from typing import Any
import datetime
import logging
import os
import pandas as pd
import pathlib
import pytz
import zoltpy.covid19

from forecast_validation import (
    ParseDateError, RepositoryRelativeFilePath
)
from forecast_validation.checks.forecast_file_content import (
    validate_forecast_values
)
from forecast_validation.validation import ValidationStepResult

logger = logging.getLogger("hub-validations")

def get_all_forecast_filepaths(
    store: dict[str, Any]
) -> ValidationStepResult:
    directory: pathlib.Path = store["HUB_MIRRORED_DIRECTORY_ROOT"]
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
    correctly_formatted_files: set(os.PathLike) = set()
    population_dataframe_path: pathlib.Path = store["POPULATION_DATAFRAME_PATH"]

    for file in files:
        file_result = zoltpy.covid19.validate_quantile_csv_file(file)
        if file_result == "no errors":
            correctly_formatted_files.add(file)
        else:
            file_result = [
                f"Error when validating format for {file}: " + e
                for e in file_result
            ]
            success = False
            error_list = errors.get(file, [])
            error[file] = error_list.extend(file_result)
            for error in file_result:
                logger.error(error)

    for file in files:
        if file not in correctly_formatted_files:
            success = False
            error_list = errors.get(file, [])
            error[file] = error_list.append((
                f"Error when validating forecast values for {file}: "
                "skipped due to incorrect file format "
            ))
        else:
            file_result = validate_forecast_values(
                file, population_dataframe_path
            )
            if file_result is not None:
                success = False
                error_list = errors.get(file, [])
                error[file] = error_list.append((
                    f"Error when validating forecast values for {file}: "
                    f"{file_result}"
                ))

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
        
        logger.info(
            (
                "Checking if the date in %s's filename matches the date inside "
                "said forecast file..."
            ),
            basename
        )

        # read only the forecast date column to save space
        try:
            df = pd.read_csv(filepath, usecols=[forecast_date_column_name])
        except ValueError:
            logger.error(
                "Forecast file %s is missing the %s column",
                basename, forecast_date_column_name
            )
            return ValidationStepResult(
                success=False,
                file_errors={filepath: [(
                    f"{basename} must have a column named "
                    f"{forecast_date_column_name} that contains the forecast "
                    "date of the file."
                )]}
            )
        except ParseDateError as pde:
            return ValidationStepResult(
                success=False,
                file_errors={filepath: [(
                    f"column {forecast_date_column_name} contains dates that "
                    "are not in the YYYY-MM-DD format; specifically, \n\t"
                    + pde.args[0]
                )]}
            )

        # extract date from filename
        file_forecast_date = datetime.datetime.strptime(
            os.path.basename(basename)[:10], "%Y-%M-%d"
        ).date()

        # filter all possible forecast dates into a set for unique check
        forecast_dates = {
            datetime.datetime.strptime(d, "%Y-%M-%d").date()
            for d in df['forecast_date']
        }

        # forecast date must be unique in CSV
        if len(forecast_dates) > 1:
            logger.info(
                "Forecast date in the %s column is not unique",
                forecast_date_column_name
            )
            success = False
            error = errors.get(filepath, "")
            errors[filepath] = [error + (
                f"{basename} has multiple forecast dates: "
                f"{forecast_dates}. There must only be one unique "
                "forecast date in one forecast file.\n"
            )]
        
        # forecast dates must match
        while len(forecast_dates) > 0:
            forecast_date = forecast_dates.pop()
            if (file_forecast_date != forecast_date):
                logger.error(
                    "Forecast dates do not match: %s vs %s",
                    str(file_forecast_date),
                    str(forecast_date)
                )
                success = False
                error = errors.get(filepath, [])
                errors[filepath] = error.append(
                    f"date in {basename} does not match date in "
                    f"`forecast_date` column: {file_forecast_date} vs "
                    f"{forecast_date}.\n"
                )
        
            # forecast dates must be <1day within each other
            today = datetime.datetime.now(pytz.timezone('US/Eastern')).date()
            if abs(file_forecast_date - today) > datetime.timedelta(days=1):
                success = False
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
