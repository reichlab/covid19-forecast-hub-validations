import pandas as pd
import os
import pytz
import datetime

from forecast_validation.validation import ValidationStepResult

def check_filename_match_forecast_date(
    filepath: str,
    forecast_date_column_name: str = "forecast_date"
) -> ValidationStepResult:
    
    # read only the forecast date column to save space
    try:
        df = pd.read_csv(filepath, usecols=[forecast_date_column_name])
    except ValueError:
        return (
            True,
            (
                f"FORECAST DATE ERROR: {filepath} must have a column "
                f"named {forecast_date_column_name} that contains the forecast "
                "date of the file"
            )
        )

    # extract date from filename
    file_forecast_date = os.path.basename(os.path.basename(filepath))[:10]

    # filter all possible forecast dates into a set for unique check
    forecast_dates = set(df['forecast_date'])

    # forecast date must be unique in CSV
    if len(forecast_dates) > 1:
        return (
            True,
            (
                f"FORECAST DATE ERROR: {filepath} has multiple forecast dates: "
                f"{forecast_dates}. There must only be one unique "
                "forecast date in one forecast file."
            )
        )
    
    # forecast dates must match
    forecast_date = forecast_dates.pop()
    if (file_forecast_date != forecast_date):
        return (
            True,
            (
                f"FORECAST DATE ERROR: {filepath}, forecast filename date "
                f"{file_forecast_date} does match forecast_date column "
                f"{forecast_date}"
            )
        )
    
    # forecast dates must be <1day within each other
    today = datetime.datetime.now(pytz.timezone('US/Eastern')).date()
    forecast_date = datetime.datetime.strptime(
        file_forecast_date, "%Y-%m-%d"
    ).date()
    if abs(forecast_date.day - today.day) > datetime.timedelta(days=1):
        warning = (
            f"Warning: The forecast file {filepath} is not made today. "
            f"date of the forecast - {file_forecast_date}, today - {today}."
        )
        print(
            f"::warning file={os.path.basename(os.path.basename(filepath))}"
            f"::{warning}"
        )
        return True, warning
    else:
        return False, "no errors"
