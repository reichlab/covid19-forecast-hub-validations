from typing import Optional
import dataclasses

from pandas.core.indexing import is_label_like

@dataclasses.dataclass(frozen=True)
class RetractionCheckResult:
    """
    Data class to store the result of a retraction check. The `success` field
    is required for initialization.

    See https://docs.python.org/3.9/library/dataclasses.html?highlight=dataclasses
    for how data classes work.

    Fields:
        success: True if the step does not contain validation errors, False if
            it does
        to_store: a dictionary containing artifacts that subsequent validation
            step(s) may use
        forecast_files: a set of forecast file paths that subsequent validation
            step(s) may use to validation individually
        label: a set of PyGithub Label objects that this validation step wants
            to apply to the PR that triggered the validation run, if applicable
        comments: a list of comments that this validation step wants to apply
            to the PR that triggered the validation run, if applicable
        errors: a dictionary that contains any and all possible validation
            error(s) that are specific to forecast files; keyed by file path
    """
    error: Optional[str]
    has_implicit_retraction: bool = False,
    has_explicit_retraction: bool = False,
    is_all_duplicate: bool = False,

    @property
    def has_no_retraction_or_duplication(self) -> bool:
        return not(
            self.has_implicit_retraction or
            self.has_explicit_retraction or
            self.is_all_duplicate
        )
        