import datetime
import logging
import pandas as pd
import pathlib
import os


logger = logging.getLogger()

def date_parser(date_str: str) -> datetime.date:
    try:
        year, month, day = date_str.split("-")
    except ValueError as ve:
        error_message = (
            "error while parsing date string %s: too many components "
            "(found 4 dashes in date string; should only have 3)"
        )
        logger.error(error_message, date_str)
        raise ValueError(error_message)
    
    if len(month) != 2:
        error_message = (
            "error while parsing date string %s: must have 2-digit month"
        ),
        logger.error(error_message, date_str)
        raise ValueError(error_message)

    if len(day) != 2:
        error_message = (
            "error while parsing date string %s: must have 2-digit day"
        ),
        logger.error(error_message, date_str)
        raise ValueError(error_message)

    return datetime.datetime.strptime(date_str, "%Y-%M-%d").date()

p = ((pathlib.Path(os.getcwd()))/"..").resolve()
p = (p/"covid19-forecast-hub"/"data-processed"/"COVIDhub-baseline"/"2021-10-04-COVIDhub-baseline.csv").resolve()
df = pd.read_csv(p, usecols=["forecast_date"], parse_dates=["forecast_date"], date_parser=date_parser)