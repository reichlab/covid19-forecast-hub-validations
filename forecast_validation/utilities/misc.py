from typing import Union
import os
import urllib.request

def fetch_url(url: str, to_path: Union[str, os.PathLike]) -> str:
    urllib.request.urlretrieve(url, to_path)
    return to_path

def compile_output_errors(
    is_filename_error,
    filename_error_output,
    is_error,
    forecast_error_output
):
    """
    purpose: update locally_validated_files.csv and remove deleted files

    params:
    * filepath: Full filepath of the forecast
    * is_filename_error: Filename != file path (True/False)
    * filename_error_output: Text output error filename != file path
    * is_error: Forecast file has error (True/False)
    * forecast_error_output: Text output forecast file error
    * is_date_error: forecast_date error (True/False)
    * forecast_date_output: Text output forecast_date error
    """
    # Initialize output errors as list
    output_error_text = []

    # Iterate through params
    error_bool = [is_filename_error, is_error]
    error_text = [filename_error_output, forecast_error_output]

    # Loop through all possible errors and add to final output
    for i in range(len(error_bool)):
        if error_bool[i]:  # Error == True
            output_error_text += error_text[i]

    # Output errors if present as dict
    # Output_error_text = list(chain.from_iterable(output_error_text))
    return output_error_text
