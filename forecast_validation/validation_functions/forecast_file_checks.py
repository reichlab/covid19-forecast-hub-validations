from typing import Any
import pathlib
import os

from forecast_validation.validation import ValidationStepResult

def get_all_forecast_and_metadata_filepaths(
    store: dict[str, Any]
) -> ValidationStepResult:
    directory: pathlib.Path = store["FORECASTS_DIRECTORY"]
    return ValidationStepResult(
        success=True,
        forecast_files={filepath for filepath in directory.glob("*.csv")}
    )


