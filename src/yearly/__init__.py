"""yearly FastAPI backend."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("yearly")
except PackageNotFoundError:
    __version__ = "0.0.0"
