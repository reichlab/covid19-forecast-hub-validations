from typing import Union
import enum
import os
import pathlib

REPOSITORY_ROOT_ONDISK: pathlib.Path = (
    pathlib.Path(__file__)/".."
).resolve()

class PullRequestFileType(enum.Enum):
    """Represents different types of files in a PR.
    """
    FORECAST = enum.auto()
    METADATA = enum.auto()
    OTHER_FS = enum.auto()
    OTHER_NONFS = enum.auto()

class RepositoryRelativeFilePath(os.PathLike):
    def __init__(self, path: Union[str, os.PathLike]):
        self._path: pathlib.Path

        path = pathlib.Path(path)
        if path.is_absolute():
            try:
                self._path = path.relative_to(REPOSITORY_ROOT_ONDISK)
            except ValueError:
                raise FilePathError((
                    "cannot create a file path that is not a subpath of the "
                    "path of the repository on disk"
                ))
        else:
            self._path = path
        
    def __fspath__(self) -> str:
        return self._path
    pass

    @property
    def exists(self) -> bool:
        return (REPOSITORY_ROOT_ONDISK/self._path).exists()


class FilePathError(BaseException):
    pass

class ParseDateError(BaseException):
    pass
