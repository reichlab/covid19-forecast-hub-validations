from typing import Union
import datetime
import logging
import os
import pandas as pd

from forecast_validation import ParseDateError

logger: logging.Logger = logging.getLogger("hub-validations")

def compare_forecasts(
    old_forecast_file_path: Union[str, os.PathLike],
    new_forecast_file_path: Union[str, os.PathLike]
) -> bool:
    """
    Compare the 2 forecasts and returns whether there are any implicit retractions or not

    Args:
        old: Either a file pointer or a path string.
        new: Either a file pointer or a path string.

    Returns:
        Whether this update has a retraction or not
    """
    columns: list[str] = [
        "forecast_date",
        "target",
        "target_end_date",
        "location",
        "type",
        "quantile"
    ]
    old_df: pd.DataFrame = pd.read_csv(
        old_forecast_file_path,
        index_col=columns
    )
    new_df: pd.DataFrame = pd.read_csv(
        new_forecast_file_path,
        index_col=columns
    )

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

def date_parser(date_str: str) -> datetime.date:
    try:
        year, month, day = date_str.split("-")
    except ValueError as ve:
        error_message = (
            "error while parsing date string %s: too many components "
            "(found 4 dashes in date string; should only have 3)"
        )
        logger.error(error_message, date_str)
        raise ParseDateError(error_message)
    
    if len(month) != 2:
        error_message = (
            "error while parsing date string %s: must have 2-digit month"
        ),
        logger.error(error_message, date_str)
        raise ParseDateError(error_message)

    if len(day) != 2:
        error_message = (
            "error while parsing date string %s: must have 2-digit day"
        ),
        logger.error(error_message, date_str)
        raise ParseDateError(error_message)

    return datetime.datetime.strptime(date_str, "%Y-%M-%d").date()
