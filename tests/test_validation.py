import unittest

from forecast_validation.validation import *

class TestValidationStepResult(unittest.TestCase):
    def test_init_with_missing_success_argument_should_throw_error(self):
        with self.assertRaises(TypeError):
            _ = ValidationStepResult()

if __name__ == "__main__":
    unittest.main()