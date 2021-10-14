from typing import Optional, Iterable
from github import Github
from github.File import File
from github.Repository import Repository
import os
import re

from forecast_validation.files import FileType

def match_file(
    file: File, patterns: dict[FileType, re.Pattern]
) -> list[FileType]:
    """Returns the type of the file given the filename.

    Uses FILENAME_PATTERNS dictionary in the configuration section
    to do the filename-filetype matching.

    Args:
        file: A PyGithub File object representing the file to match.

    Returns:
        A list of all possible file types that the file matched on.
    """
    matched = []
    for filetype in patterns:
        if patterns[filetype].match(file.filename):
            matched.append(filetype)
    if len(matched) == 0:
        matched.append[FileType.OTHER_NONFS]

    return matched

def filter_files(
    files: Iterable[File],
    patterns: dict[FileType, re.Pattern]
) -> dict[FileType, list[File]]:
    """Filters a list of filenames into corresponding file types.

    Uses match_file() to match File to FileType.

    Args:
        files: List of PyGithub File objects.

    Returns:
        A dictionary keyed by the type of file and contains a list of Files
        of that type as value.
    """
    filtered_files: dict[FileType, list[File]] = {}
    for file in files:
        file_types: list[FileType] = match_file(file, patterns)
        for file_type in file_types:
            if file_type not in filtered_files:
                filtered_files[file_type] = [file]
            else:
                filtered_files[file_type].append(file)
    
    return filtered_files

def is_forecast_submission(
    filtered_files: dict[FileType, list[File]]
) -> bool:
    """Checks types of files to determine if the PR is a forecast submission.

    There must be at least one file that is not of type `FileType.OTHER_NONFS`.
    To see how file types are determined, check the `FILENAME_PATTERNS`
    dictionary in the configuration section or a similar dictionary passed into
    a preceding call of `filter_files()`.

    Args:
        filtered_files: A dictionary containing lists of PyGithub File objects
          mapped to their type.

    Returns:
        True if the given file dictionary represents a forecast submission PR,
        False if not.
    """

    # TODO: this is really better done by separating the data repository from
    # code that runs on that repository. However, that is a super big change,
    # so more discussion and decision-making is required.

    return (FileType.FORECAST in filtered_files or
            FileType.METADATA in filtered_files or
            FileType.OTHER_FS in filtered_files)
