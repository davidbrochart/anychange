import importlib.metadata

from .main import awatch
from .watcher import AllWatcher, Change, DefaultDirWatcher, DefaultWatcher, PythonWatcher, RegExpWatcher

try:
    __version__ = importlib.metadata.version('anychange')
except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = 'unknown'

__all__ = (
    'awatch',
    'Change',
    'AllWatcher',
    'DefaultDirWatcher',
    'DefaultWatcher',
    'PythonWatcher',
    'RegExpWatcher',
)
