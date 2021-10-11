import inspect
from logging import log
from types import MappingProxyType
from typing import Any, Optional, Callable, Union
from github.Label import Label
import dataclasses
import os

@dataclasses.dataclass(frozen=True)
class ValidationStepResult:
    """
    Data class to store the result of a validation step. The fields `success`
    and `fatal` are parameters required to create a ValidationStepResult object.

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
    to_store: Optional[dict] = None
    forecast_files: Optional[set[os.PathLike]] = None
    labels: Optional[set[Label]] = None
    comments: Optional[list[str]] = None
    file_errors: Optional[dict[os.PathLike, str]] = None

class ValidationStep:
    @staticmethod
    def check_logic(logic: Callable) -> None:
        if logic is not None and not isinstance(logic, Callable):
            raise TypeError("logic must be a Callable (i.e., function)")

    def __init__(self, logic: Optional[Callable] = None) -> None:
        ValidationStep.check_logic(logic)
        self._executed: bool = False
        self._result: Optional[ValidationStepResult] = None
        self._logic: Optional[Callable] = logic

    def __init__(self) -> None:
        self(logic=None)

    @property
    def executed(self) -> bool:
        return self._executed

    @property
    def success(self) -> Optional[bool]:
        return None if self._result is None else self._result.success

    @property
    def has_logic(self) -> bool:
        return self._logic is not None

    @property
    def logic(self) -> Optional[Callable]:
        return self._logic

    @logic.setter
    def logic(self, new_logic: Optional[Callable]) -> None:
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
            if not isinstance(result, ValidationStepResult):
                raise RuntimeError("validation step result type mismatch")

class ValidationPerFileStep(ValidationStep):
    def execute(
        self,
        store: dict[str, Any],
        files: set[os.PathLike]
    ) -> ValidationStepResult:
        if self._logic is None:
            raise RuntimeError("validation step has no logic")
        else:
            parameters = set(inspect.signature(self._logic).parameters)
            
            if "files" not in parameters:
                raise RuntimeError((
                    "per-file validation step must contain logic that takes "
                    "a parameter called `files` on which to run the per-file "
                    "logic"
                ))
            
            if "store" in parameters:
                result = self._logic(store=store, files=files)
            else:
                result = self._logic(files=files)

            self._executed = True
            if not isinstance(result, ValidationStepResult):
                raise RuntimeError("validation step result type mismatch")

class ValidationRun:
    def __init__(
        self,
        steps: list[ValidationStep] = []
    ) -> None:
        self._steps: list[ValidationStep] = steps
        self._forecast_files: set[os.PathLike] = None
        self._store: dict = {}

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

        self._upload_labels_comments_and_errors()

    def _upload_labels_comments_and_errors(self):
        pass
