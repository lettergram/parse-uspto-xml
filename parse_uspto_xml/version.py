"""Package version number."""

MAJOR = 0
MINOR = 1
MICRO = 0
POST = None

_post_str = f".post{POST}" if POST else ""
__version__ = f"{MAJOR}.{MINOR}.{MICRO}" + _post_str
