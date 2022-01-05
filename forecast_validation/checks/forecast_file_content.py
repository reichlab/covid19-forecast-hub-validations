from typing import Optional, Tuple, Union
import datetime
import logging
import numpy as np
import os
import pandas as pd
from pandas.io.stata import invalid_name_doc
import zoltpy.covid19

from forecast_validation import ParseDateError
from forecast_validation.checks import RetractionCheckResult
from forecast_validation.utilities.misc import compile_output_errors

logger: logging.Logger = logging.getLogger("hub-validations")

def compare_forecasts(
    old_forecast_file_path: Union[str, os.PathLike],
    new_forecast_file_path: Union[str, os.PathLike]
) -> RetractionCheckResult:
    """
    Compare the 2 forecasts and returns whether there are any implicit retractions or not

    Args:
        old: Either a file pointer or a path string.
        new: Either a file pointer or a path string.

    Returns:
        Whether this update has a retraction or not
    """
    old_df: pd.DataFrame = pd.read_csv(
        old_forecast_file_path,
        index_col=["forecast_date", "target", "target_end_date", "location",
                   "type", "quantile"])
    new_df: pd.DataFrame = pd.read_csv(
        new_forecast_file_path,
        index_col=["forecast_date", "target", "target_end_date", "location",
                   "type", "quantile"])

    error: Optional[str] = None
    has_implicit_retraction: bool = False
    has_explicit_retraction: bool = False
    is_all_duplicate: bool = False
    
    # First check if new dataframe has entries for ALL values of old dataframe
    try:
        # Access the indices of old forecast file in the new one
        # TODO: There is definitely a more elegant way to do this!
        new_vals = new_df.loc[old_df.index]
        comparison = (old_df == new_vals)
        if ((comparison).all(axis=None)) & (len(old_df) == len(new_df)):
            is_all_duplicate = True
            error = "Forecast is all duplicate."
    except KeyError as e:
        error = f"implicit retractions: {e.args[0]}"
        # New forecast has some indices that are NOT in old forecast
        has_implicit_retraction = True
    else:   
        # check for explicit retractions
        # check if mismatched positions have NULLs
        if not (comparison).all(axis=None):
            if ((new_vals.isnull()) & (~ comparison)).any(axis=None):
                has_explicit_retraction = True
    return RetractionCheckResult(
        error=error,
        has_implicit_retraction=has_implicit_retraction,
        has_explicit_retraction=has_explicit_retraction,
        is_all_duplicate=is_all_duplicate
    )

def check_date_format(date_str: str) -> None:
    try:
        _, month, day = date_str.split("-")
    except ValueError as ve:
        error_message = (
            f"error while parsing date string {date_str}; too many components "
            "(found 4 dashes in date string; should only have 3)"
        )
        logger.error(error_message, date_str)
        raise ParseDateError(error_message)
    
    if len(month) != 2:
        error_message = (
            f"error while parsing date string {date_str}; must have 2-digit "
            "month"
        )
        logger.error(error_message, date_str)
        raise ParseDateError(error_message)

    if len(day) != 2:
        error_message = (
            f"error while parsing date string {date_str}; must have 2-digit day"
        )
        logger.error(error_message, date_str)
        raise ParseDateError(error_message)

def validate_forecast_values(
    forecast_file_path: os.PathLike,
    population_dataframe_path: os.PathLike
) -> Optional[str]:
    '''
        Get the numer of invalid predictions in a forecast file.
        
        What counts as an `invalid` prediction? 
            - A prediction who's `value` is greater than the population of that
              region. 

        Method:
        1. convert the location column to an integer (so that we can do an
           efficient `join` with the forecast DataFrame)
        2. Do a left join of the forecast DataFrame with population dataframe
           on the `location` column.
        3. Find number of rows that have the value in `value` column >= the 
           value of the `Population` column.

        Population data: 
        Retrieved from the JHU timeseries data used for generating the truth 
        data file. (See /data-locations/populations.csv)
        County population aggregated to state and state thereafter aggregated 
        to national. 
    '''
    model_dataframe = pd.read_csv(forecast_file_path, dtype={'location': str})
    population_dataframe = (
        pd.read_csv(population_dataframe_path, dtype={"location": str})
    )

    merged = model_dataframe.merge(
        population_dataframe[['location', 'population']],
        on='location', how='left'
    )
    invalid_predictions = merged['value'] >= merged['population']
    num_invalid_predictions = np.sum(invalid_predictions)

    if num_invalid_predictions > 0:
        return (
            f"Found {num_invalid_predictions} predictions with forecasted "
            "value larger than population size of locality in your file, "
            "at row(s) "
            f"{list(merged[invalid_predictions].index)}"
        )
    else:
        return None
