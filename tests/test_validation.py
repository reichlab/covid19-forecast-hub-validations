import unittest
import unittest.mock

from forecast_validation.validation import *

class TestValidationStepResult(unittest.TestCase):
    def test_init_with_missing_success_argument_should_throw_TypeError(self):
        """ValidationStepResult() test: Missing success argument

        This should throw a TypeError.
        """
        with self.assertRaises(TypeError):
            ValidationStepResult()

class TestValidationStep(unittest.TestCase):

    # ---- check_logic() tests ----

    def test_check_logic_with_non_Callable_logic_should_throw_TypeError(self):
        """ValidationStep.check_logic() test: non Callable argument
        """
        with self.assertRaises(TypeError):
            ValidationStep.check_logic("not a callable")

    # ---- __init__(self) tests ----

    def test_init_with_non_Callable_logic_should_throw_TypeError(self):
        """ValidationStep() test: non Callable argument
        """
        with self.assertRaises(TypeError):
            ValidationStep("not a callable")

    def test_executed_property_before_execute_should_return_False(self):
        """ValidationStep step.executed test: before step.execute()
        """
        step = ValidationStep()

        self.assertFalse(step.executed)

    def test_executed_property_after_execute_should_return_True(self):
        """ValidationStep step.executed test: after step.execute()
        """
        step = ValidationStep()
        def execute_effect():
            step._executed = True
        step.execute = unittest.mock.MagicMock(
            side_effect=execute_effect
        )

        step.execute()

        self.assertTrue(step.executed)

    def test_success_property_before_execute_should_return_None(self):
        """ValidationStep step.success test: before step.execute()
        """
        step = ValidationStep()

        self.assertIsNone(step.success)

    def test_success_property_after_successful_execute_should_return_True(self):
        """ValidationStep step.success test: after step.execute(), no errors
        """
        step = ValidationStep()
        def execute_effect():
            step._executed = True
            step._result = ValidationStepResult(True)
        step.execute = unittest.mock.MagicMock(
            side_effect=execute_effect
        )
        
        step.execute()

        self.assertTrue(step.success)

    def test_success_property_after_failed_execute_should_return_False(self):
        """ValidationStep step.success test: after step.execute(), errors
        """
        step = ValidationStep()
        def execute_effect():
            step._executed = True
            step._result = ValidationStepResult(False)
        step.execute = unittest.mock.MagicMock(
            side_effect=execute_effect
        )
        
        step.execute()

        self.assertFalse(step.success)

    def test_has_logic_property_with_None_logic_should_return_False(self):
        """ValidationStep step.has_logic test: no logic
        """
        step = ValidationStep()

        self.assertFalse(step.has_logic)

    def test_has_logic_property_with_Callable_logic_should_return_True(self):
        """ValidationStep step.has_logic test: Callable logic
        """
        step = ValidationStep(unittest.mock.MagicMock())

        self.assertTrue(step.has_logic)

    def test_logic_property_with_None_logic_should_return_None(self):
        """ValidationStep step.logic test: no logic
        """
        step = ValidationStep()

        self.assertIsNone(step.logic)

    def test_logic_property_with_Callable_logic_should_return_logic(self):
        """ValidationStep step.logic test: Callable logic
        """
        mock_logic = unittest.mock.MagicMock()
        step = ValidationStep(mock_logic)

        self.assertIs(step.logic, mock_logic)

    def test_set_logic_with_non_Callable_logic_should_throw_error(self):
        """ValidationStep step.logic() test: logic="not a Callable"
        """
        step = ValidationStep(unittest.mock.MagicMock())

        with self.assertRaises(TypeError):
            step.set_logic("not a Callable")
    
    def test_set_logic_with_None_logic_should_clear_logic(self):
        """ValidationStep step.logic() test: logic=None
        """
        step_1 = ValidationStep(unittest.mock.MagicMock())
        step_1.set_logic(None)

        step_2 = ValidationStep(None)
        step_2.set_logic(None)

        self.assertFalse(step_1.has_logic)
        self.assertFalse(step_2.has_logic)

    def test_set_logic_with_Callable_logic_should_change_logic(self):
        """ValidationStep step.logic() test: logic=<some Callable>
        """
        mock_logic_1 = unittest.mock.MagicMock()
        step1 = ValidationStep(mock_logic_1)
        step1.set_logic(unittest.mock.MagicMock())

        step2 = ValidationStep(None)
        step2.set_logic(unittest.mock.MagicMock())

        self.assertTrue(step1.has_logic)
        self.assertTrue(step2.has_logic)
        self.assertIsNot(step1.logic, mock_logic_1)

    def test_execute_with_no_logic_should_throw_error(self):
        """ValidationStep step.execute() test: no logic
        """
        step = ValidationStep()

        with self.assertRaises(RuntimeError):
            step.execute({})

    def test_execute_with_wrong_return_type_logic_should_throw_error(self):
        """ValidationStep step.execute() test: logic return type incorrect
        """
        step = ValidationStep(
            unittest.mock.MagicMock(
                return_value="not ValidationResult"
            )
        )

        with self.assertRaises(RuntimeError):
            step.execute({})

    def test_execute_with_no_store_logic_should_call_with_no_store(self):
        """ValidationStep step.execute() test: logic without store parameter
        """
        no_store_logic = unittest.mock.MagicMock(
            return_value=ValidationStepResult(True)
        )
        step = ValidationStep(no_store_logic)

        step.execute({})

        no_store_logic.assert_called_once_with()
    
    def test_execute_with_store_logic_should_call_with_store(self):
        """ValidationStep step.execute() test: logic with store parameter
        """
        logic = unittest.mock.MagicMock(
            __signature__=inspect.signature(lambda store: None),
            return_value=ValidationStepResult(True)
        )
        step = ValidationStep(logic)
        store = {}

        step.execute(store)

        logic.assert_called_once_with(store=store)


if __name__ == "__main__":
    unittest.main()
