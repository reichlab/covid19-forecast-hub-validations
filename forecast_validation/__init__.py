import enum

class PullRequestFileType(enum.Enum):
    """Represents different types of files in a PR.
    """
    FORECAST = enum.auto()
    METADATA = enum.auto()
    OTHER_FS = enum.auto()
    OTHER_NONFS = enum.auto()
