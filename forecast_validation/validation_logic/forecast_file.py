from typing import Any
import pathlib
import os
import zoltpy.covid19

from forecast_validation.validation import ValidationStepResult

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