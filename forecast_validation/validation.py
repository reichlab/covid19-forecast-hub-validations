from __future__ import annotations
from typing import Any, Iterable, Optional, Callable
from github.File import File
from github.Label import Label
import dataclasses
import inspect
import logging
import os

from github.PullRequest import PullRequest

from forecast_validation import (
    PullRequestFileType,
    VALIDATIONS_VERSION
)

logger = logging.getLogger("hub-validations")

@dataclasses.dataclass(frozen=True)
class ValidationStepResult:
    """
    Data class to store the result of a validation step. The `success` field
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
    success: bool
    skip_steps_after: bool = False
    to_store: Optional[dict[str, Any]] = None
    forecast_files: Optional[set[os.PathLike]] = None
    labels: Optional[set[Label]] = None
    comments: Optional[list[str]] = None
    file_errors: Optional[dict[os.PathLike, list[str]]] = None

class ValidationStep:
    @staticmethod
    def check_logic(logic: Optional[Callable]) -> None:
        if logic is not None and not isinstance(logic, Callable):
            raise TypeError("logic must be a Callable (i.e., function)")

    def __init__(self, logic: Optional[Callable] = None) -> None:
        ValidationStep.check_logic(logic)
        self._executed: bool = False
        self._result: Optional[ValidationStepResult] = None
        self._logic: Optional[Callable] = logic

    @property
    def executed(self) -> bool:
        return self._executed

    @property
    def success(self) -> Optional[bool]:
        return None if self._result is None else self._result.success

    @property
    def result(self) -> Optional[ValidationStepResult]:
        return self._result

    @property
    def has_logic(self) -> bool:
        return self._logic is not None

    @property
    def logic(self) -> Optional[Callable]:
        return self._logic

    def set_logic(self, new_logic: Optional[Callable]) -> None:
        """Sets or clears the logic of the validation step.

        If None is given, then the logic is cleared. Otherwise,
        the given logic is assigned to the validation step.

        Args:
            logic: 
        """
        ValidationStep.check_logic(new_logic)     
        self._logic = new_logic

    def execute(self, store: dict[str, Any]) -> ValidationStepResult:
        if self._logic is None:
            raise RuntimeError("validation step has no logic")
        else:
            needs_store: bool = (
                "store" in set(inspect.signature(self._logic).parameters)
            )

            if needs_store:
                result = self._logic(store=store)
            else:
                result = self._logic()


            self._executed = True
            self._result = result
            if not isinstance(result, ValidationStepResult):
                raise RuntimeError("validation step result type mismatch")

            return result
            

class ValidationPerFileStep(ValidationStep):

    def check_logic(logic: Callable) -> None:
        ValidationStep.check_logic(logic)
        
        parameters = set(inspect.signature(logic).parameters)
        if "files" not in parameters:
            raise ValueError((
                "per-file validation step must contain logic that takes "
                "a parameter called `files` on which to run the per-file "
                "logic"
            ))

    def execute(
        self,
        store: dict[str, Any],
        files: set[os.PathLike]
    ) -> ValidationStepResult:
        if self._logic is None:
            raise RuntimeError("validation step has no logic")
        else:
            parameters = set(inspect.signature(self._logic).parameters)
            if "store" in parameters:
                result = self._logic(store=store, files=files)
            else:
                result = self._logic(files=files)

            self._executed = True
            self._result = result
            if not isinstance(result, ValidationStepResult):
                raise RuntimeError("validation step result type mismatch")

            return result

class ValidationRun:
    def __init__(
        self,
        steps: list[ValidationStep] = []
    ) -> None:
        self._steps: list[ValidationStep] = steps
        self._forecast_files: set[os.PathLike] = set()
        self._store: dict[str, Any] = {}

    def run(self):
        for step in self._steps:
            assert isinstance(step, ValidationStep), step

            if isinstance(step, ValidationPerFileStep):
                result: ValidationStepResult = step.execute(
                    self._store, self._forecast_files
                )
            else:
                result: ValidationStepResult = step.execute(self._store)
            
            if result.to_store is not None:
                self._store |= result.to_store
            elif result.forecast_files is not None:
                self._forecast_files |= result.forecast_files

            if result.skip_steps_after:
                logger.info("Skipping the rest of validation steps")
                break

        # apply labels, comments, and errors to pull request
        # if applicable
        if (
            "pull_request" in self._store and
            "filtered_files" in self._store and
            "possible_labels" in self._store
        ):   
            self._upload_results_to_pull_request_and_automerge_check()

    @property
    def store(self) -> dict[str, Any]:
        return self._store

    @property
    def validation_steps(self) -> list[ValidationStep]:
        return self._steps

    @property
    def executed_steps(self) -> Iterable[ValidationStep]:
        """The steps that were executed during this run.

        Returns:
            an iterator that iterates over all executed steps in this
        run.
        """
        return filter(lambda s: s.executed, self._steps)

    @property
    def success(self) -> bool:
        return all(
            [s.success for s in self.executed_steps]
        )

    def _upload_results_to_pull_request_and_automerge_check(self):
        pull_request: PullRequest = self._store["pull_request"]
        filtered_files: dict[PullRequestFileType, list[File]] = (
            self._store["filtered_files"]
        )
        all_labels: dict[str, Label] = self._store["possible_labels"]
        
        # if true, add additional automerge PR label
        automerge: bool = self._store["AUTOMERGE"]

        # merge all labels, comments, and errors generated at each step
        labels: set[Label] = set()
        comments: list[str] = []
        errors: dict[os.PathLike, list[str]] = {}
        for step in self.executed_steps:
            if step.result.labels is not None:
                labels |= step.result.labels
            if step.result.comments is not None:
                comments.extend(step.result.comments)
            if step.result.file_errors is not None:
                for filepath in step.result.file_errors:
                    if filepath in errors:
                        errors[filepath].extend(
                            step.result.file_errors[filepath]
                        )
                    else:
                        errors[filepath] = (
                            step.result.file_errors[filepath].copy()
                        )

        no_errors: bool = len(errors) == 0
        has_non_csv_or_metadata: bool = (
            len(filtered_files.get(PullRequestFileType.METADATA, [])) +
            len(filtered_files.get(PullRequestFileType.OTHER_NONFS, []))
        ) != 0
        only_one_forecast_csv: bool = (
            len(filtered_files.get(PullRequestFileType.FORECAST, [])) == 1
        )
        all_csvs_in_correct_location: bool = (
            len(filtered_files.get(PullRequestFileType.OTHER_FS, [])) == 0
        )

        if (len(labels) == 1 and
            all_labels["data-submission"] in labels and
            no_errors and 
            not has_non_csv_or_metadata and 
            all_csvs_in_correct_location and
            only_one_forecast_csv
        ):
            if automerge:
                logger.info("PR %s can be automerged", pull_request.number)
                labels.add(all_labels['automerge'])

        # apply labels, comments, and errors (if any) to pull request on GitHub
        if len(labels) > 0:
            logger.info("Labels to be applied: %s", str(labels))
            pull_request.set_labels(*list(labels))
        else:
            logger.info("No labels to be applied")
        if len(comments) > 0:
            pull_request.create_issue_comment(
                f"### Validations v{VALIDATIONS_VERSION}\n\nComments:\n\n"
                + "\n\n".join(comments)
            )
        if self.success:
            # note: covid hub will also have this tag when a PR passed validation
            labels.add(all_labels['passed-validation'])
            pull_request.create_issue_comment(
                f"Validations v{VALIDATIONS_VERSION}\n\n"
                "Errors: \n\n"
                "✔️ No validation errors in this PR."
            )
        else:
            error_comment = (
                f"Validations v{VALIDATIONS_VERSION}\n\n"
                "Errors: \n\n"
                "❌ There are errors in this PR. \n\n"
            )
            for path in errors:
                error_comment += f"**{path}**:\n"
                for error in errors[path]:
                    error_comment += f"{error}\n"
                error_comment += "\n"
            pull_request.create_issue_comment(error_comment.rstrip())
