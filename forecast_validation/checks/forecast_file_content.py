from typing import Optional, Tuple, Union
import datetime
import logging
import numpy as np
import os
import pandas as pd
from pandas.io.stata import invalid_name_doc
import zoltpy.covid19

from forecast_validation import ParseDateError
from forecast_validation.utilities.misc import compile_output_errors

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
        _, month, day = date_str.split("-")
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

    return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

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
    model_dataframe = pd.read_csv(forecast_file_path).astype({'location': str})
    population_dataframe = (
        pd.read_csv(population_dataframe_path).astype({"location": str})
    )

    merged = model_dataframe.merge(
        population_dataframe[['location', 'population']],
        on='location', how='left'
    )
    invalid_predictions = merged['value'] >= merged['population']
    num_invalid_predictions = np.sum(invalid_predictions)

    if num_invalid_predictions > 0:
        return (
            f"PREDICTION ERROR: You have {num_invalid_predictions} invalid "
            "predictions in your file. Invalid predictions (predicted value "
            f"greater than population of locality): \n {invalid_predictions}"
        )
    return None
