from typing import Any, Optional, Callable
class ValidationStep:

    def __init__(self, logic: Callable) -> None:
        self._executed: bool = False
        self._success: Optional[bool] = None
        self._result_message: Optional[str] = None

        if logic is not None and not isinstance(logic, Callable):
            raise TypeError("logic must be a Callable (i.e., function)")

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
    def result_message(self) -> str:
        if not self._executed:
            return 'This validation step has not executed yet'
        else:
            return self._result_message

    @property
    def has_logic(self) -> bool:
        return not self._logic

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
        # TODO: check if self has prev or next steps
        # check output type from prev
        # check input type from next
        # make sure they match
        self._logic = new_logic

    def execute(self, store: dict[str, Any]) -> Optional[NotImplemented]:
        if self._logic is None:
            raise ValueError('validation step has no logic')
        else:
            self._logic()
            self._executed = True
    
class ValidationStepResult:
    def __init__(self) -> None:
        self._to_store = None
        self._labels = None
        self._comments = None
        pass
    

class ValidationRun:
    def __init__(self, steps: list[ValidationStep]) -> None:
        self._steps = steps
        self._store = {}

    def __init__(self) -> None:
        self(steps=[])
