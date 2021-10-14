from typing import Any, Optional, Callable
from github.Label import Label
import dataclasses
import inspect
import logging
import os

from github.PullRequest import PullRequest

logger = logging.getLogger("hub-validations")

@dataclasses.dataclass(frozen=True)
class ValidationStepResult:
    """
    Data class to store the result of a validation step. The `success` field
    is required for initialization.

    See https://docs.python.org/3.9/library/dataclasses.html?highlight=dataclasses
    for how data classes work.

    Fields:
        success: True if the step does not contains validation errors, False if
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
    file_errors: Optional[dict[os.PathLike, str]] = None

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
        self._forecast_files: set[os.PathLike] = None
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
        if "pull_request" in self._store:
            pull_request: PullRequest = self._store["pull_request"]

            labels: set[Label] = set()
            comments: list[str] = ["Comments: "]
            errors: dict[os.PathLike, str] = {}
            for step in self._steps:
                if step.executed:
                    if step.result.labels is not None:
                        labels.union(step.result.labels)
                    if step.result.comments is not None:
                        comments.extend(step.result.comments)
                    if step.result.file_errors is not None:
                        errors |= step.result.file_errors

            if len(labels) > 0:
                pull_request.set_labels(list(labels))
            pull_request.create_issue_comment(
                "\n\n".join(comments)
            )
            if len(errors) == 0:
                pull_request.create_issue_comment(
                    "✔️ No validation errors in this PR."
                )
            else:
                error_comment = "❌ There are errors in this PR: \n\n"
                for path in errors:
                    error_comment += f"{path}: {errors[path]} \n"
                pull_request.create_issue_comment(error_comment.rstrip())

    @property
    def store(self) -> dict[str, Any]:
        return self._store

    @property
    def validation_steps(self) -> list[ValidationStep]:
        return self._steps

    @property
    def success(self) -> bool:
        return all([s.success for s in self._steps if s.success is not None])
