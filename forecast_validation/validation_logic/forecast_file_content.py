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
    date_parser
)
from forecast_validation.validation import ValidationStepResult

logger = logging.getLogger("hub-validations")

def get_all_forecast_filepaths(
    store: dict[str, Any]
) -> ValidationStepResult:
    directory: pathlib.Path = store["FORECASTS_DIRECTORY"]
    return ValidationStepResult(
        success=True,
        forecast_files={
            RepositoryRelativeFilePath(fp) for fp in directory.glob("*.csv")
        }
    )

def validate_forecast_files(
    store: dict[str, Any],
    files: list[os.PathLike]
) -> ValidationStepResult:

    success: bool = True
    errors: dict[os.PathLike, list[str]] = {}
    correctly_formatted_files = []

    for file in files:
        file_result = zoltpy.covid19.validate_quantile_csv_file(file)
        if file_result == "no errors":
            correctly_formatted_files.append(file)
        else:
            success = False
            error = errors.get(file, )
            logger.error()
    pass

def forecast_check(filepath: os.PathLike):
    
    forecast_errors = validate_forecast_file(filepath)

    # validate predictions
    if forecast_errors is not None:
        is_error, forecast_error_output = validate_forecast_values(filepath)
    else:
        logger.

    # Add to previously checked files
    output_error_text = compile_output_errors(
        filepath,
        False,
        [],
        is_error,
        forecast_error_output
    )
    
    return output_error_text

def check_filename_match_forecast_date(
    store: dict[str, Any],
    files: set[os.PathLike]
) -> ValidationStepResult:

    forecast_date_column_name: str = "forecast_date"
    success: bool = True
    errors: dict[os.PathLike, list[str]] = {}
    comments: list[str] = []

    for filepath in files:
        basename: str = os.path.basename(filepath)
        
        logger.info((
            "Checking if the date in %s's filename matches the date inside "
            "said forecast file...",
            basename
        ))

        # read only the forecast date column to save space
        try:
            df = pd.read_csv(filepath,
                usecols=[forecast_date_column_name],
                parse_dates=[forecast_date_column_name],
                date_parser=date_parser
            )
        except ValueError:
            logger.info(
                "%s is missing the %s column",
                basename, forecast_date_column_name
            )
            return ValidationStepResult(
                success=False,
                file_errors={filepath: (
                    f"{basename} must have a column named "
                    f"{forecast_date_column_name} that contains the forecast "
                    "date of the file."
                )}
            )
        except ParseDateError as pde:
            return ValidationStepResult(
                success=False,
                file_errors={filepath: (
                    f"column {forecast_date_column_name} contains dates that "
                    "are not in the YYYY-MM-DD format; specifically, \n\t"
                    + pde.args[0]
                )}
            )

        # extract date from filename
        file_forecast_date = os.path.basename(os.path.basename(filepath))[:10]

        # filter all possible forecast dates into a set for unique check
        forecast_dates = set(df['forecast_date'])

        # forecast date must be unique in CSV
        if len(forecast_dates) > 1:
            logger.info(
                "Forecast date in the %s column is not unique",
                forecast_date_column_name
            )
            success = False
            error = errors.get(filepath, "")
            errors[filepath] = error + (
                f"{basename} has multiple forecast dates: "
                f"{forecast_dates}. There must only be one unique "
                "forecast date in one forecast file.\n"
            )
        
        # forecast dates must match
        while len(forecast_dates) > 0:
            forecast_date = forecast_dates.pop()
            if (file_forecast_date != forecast_date):
                logger.info(
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
            forecast_date = datetime.datetime.strptime(
                file_forecast_date, "%Y-%m-%d"
            ).date()
            if abs(forecast_date.day - today.day) > datetime.timedelta(days=1):
                success = False
                comments.append((
                    f"⚠️ Warning: The forecast file {filepath} is not made "
                    f"today. date of the forecast - {file_forecast_date}, "
                    f"today - {today}."
                ))
                logger.info(
                    "Forecast file %s is made more than 1 day ago.",
                    basename
                )
    
    return ValidationStepResult(
        success=success,
        comments=comments,
        file_errors=errors
    )
