from typing import Any
import datetime
import logging
import os
import pandas as pd
import pathlib
import pytz
import zoltpy.covid19

from forecast_validation.validation import ValidationStepResult

logger = logging.getLogger("hub-validations")

def get_all_forecast_filepaths(
    store: dict[str, Any]
) -> ValidationStepResult:
    directory: pathlib.Path = store["FORECASTS_DIRECTORY"]
    return ValidationStepResult(
        success=True,
        forecast_files={filepath for filepath in directory.glob("*.csv")}
    )

def validate_forecast_files(
    store: dict[str, Any],
    files: list[os.PathLike]
) -> ValidationStepResult:

    errors: dict[os.PathLike, list[str]]

    for file in files:
        file_result = zoltpy.covid19.validate_quantile_csv_file(file)
    pass

def check_filename_match_forecast_date(
    store: dict[str, Any],
    files: set[os.PathLike]
) -> ValidationStepResult:

    forecast_date_column_name: str = "forecast_date"
    success: bool = True
    errors: dict[os.PathLike, str] = {}
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
            df = pd.read_csv(filepath, usecols=[forecast_date_column_name])
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
                error = errors.get(filepath, "")
                errors[filepath] = error + (
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
                f"⚠️ Warning: The forecast file {filepath} is not made today. "
                f"date of the forecast - {file_forecast_date}, today - {today}."
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
