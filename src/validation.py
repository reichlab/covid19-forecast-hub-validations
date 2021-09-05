from typing import Any, Optional, Callable, Type, TypeVar, Generic
from inspect import signature

O = TypeVar('O')

class ValidationStep(Generic[O]):

    def __init__(self, logic: Callable[..., O]) -> None:
        self._executed: bool = False
        self._success: Optional[bool] = None
        self._result_message: Optional[str] = None
        self._logic: Optional[Callable[..., O]] = logic

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
    def logic(self) -> Optional[Callable[..., O]]:
        return self._logic

    @property
    def input_types(self) -> list[Type]:
        input_type = []

        input_parameters = signature(self._logic).parameters
        for parameter_name in input_parameters:
            parameter
        return [type(self._logic)]

    @property
    def output_type(self) -> Type[O]:
        return type(O)

    @logic.setter
    def logic(self, logic: Callable[...]) -> None:
        # TODO: check if self has prev or next steps
        # check output type from prev
        # check input type from next
        # make sure they match
        self._logic = logic

    def execute(self) -> Optional[NotImplemented]:
        if not self._logic:
            print('step has no logic registered')
        else:
            self._logic()
            self._executed = True
    
    

class ValidationRun:
    def __init__(self, steps: list[ValidationStep]) -> None:
        self._steps = steps

    def __init__(self) -> None:
        self(steps=[])
