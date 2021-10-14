import unittest
import unittest.mock

import os

from forecast_validation.validation_functions.github_connection import (
    establish_github_connection,
    Github
)

class TestGitHubConnection(unittest.TestCase):

    # The point of this extensive patching is to remove
    # any external dependency during testing.
    
    # This could perhaps also be an argument to break the
    # establish_github_connection() function up into smaller
    # pieces, so that less externally-dependent functionality
    # needs to be patched.

    @unittest.mock.patch("os.getcwd", 
        new_callable=unittest.mock.MagicMock(
            return_value="/test/dir"
        )
    )
    @unittest.mock.patch.dict(os.environ, {
        "VALIDATION_VERSION": "-1",
        "GITHUB_EVENT_NAME": "mock event",
        "GITHUB_REPOSITORY": "mock repository",
    })
    @unittest.mock.patch(
        "forecast_validation.validation_functions.github_connection.Github"
    )
    def test_establish_github_connection_with_missing_GH_TOKEN(self):

        establish_github_connection()
        pass