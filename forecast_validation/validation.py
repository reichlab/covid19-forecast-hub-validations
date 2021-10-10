from logging import log
from typing import Any, Optional, Callable, Union
from github.Label import Label
import dataclasses
import os

@dataclasses.dataclass(frozen=True)
class ValidationStepResult:
    success: bool
    to_store: Optional[dict] = None
    forecast_files: Optional[list[os.PathLike]] = None
    labels: Optional[list[Label]] = None
    comments: Optional[list[str]] = None
    errors: Optional[dict[str, str]] = None

class ValidationStep:
    def check_logic(logic: Callable) -> None:
        if logic is not None and not isinstance(logic, Callable):
            raise TypeError("logic must be a Callable (i.e., function)")

    def __init__(self, logic: Callable) -> None:
        self._executed: bool = False
        self._success: Optional[bool] = None
        self._result: Optional[ValidationStepResult] = None

        ValidationStep.check_logic(logic)
        self._logic: Optional[Callable] = logic

    def __init__(self) -> None:
        self(logic=None)

    @property
    def executed(self) -> bool:
        return self._executed

    @property
    def success(self) -> Optional[bool]:
        return self._success

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
            raise ValueError("validation step has no logic")
        else:
            self._executed = True
            result = self._logic(store=store)
            if not isinstance(result, ValidationStepResult):
                raise RuntimeError("validation step result type mismatch")

class ValidationRun:
    def __init__(self, steps: list[ValidationStep]) -> None:
        self._steps: list[ValidationStep] = steps
        self._forecast_files: list[os.PathLike] = None
        self._store: dict = {}

    def __init__(self) -> None:
        self(steps=[])

    def run(self):
        for step in self._steps:
            step.execute()

        self._upload_labels_comments_and_errors()

    def _upload_labels_comments_and_errors(self):
        pass
