from enum import Enum, auto

class FileType(Enum):
    """Represents different types of files in a PR.
    """
    FORECAST = auto()
    METADATA = auto()
    OTHER_FS = auto()
    OTHER_NONFS = auto()
