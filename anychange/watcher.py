from __future__ import annotations

import logging
import os
import re
from enum import IntEnum
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING

__all__ = 'Change', 'AllWatcher', 'DefaultDirWatcher', 'DefaultWatcher', 'PythonWatcher', 'RegExpWatcher'
logger = logging.getLogger('anychange.watcher')


class Change(IntEnum):
    added = 1
    modified = 2
    deleted = 3


if TYPE_CHECKING:
    FileChange = tuple[Change, str]
    DirEntry = os.DirEntry[str]
    StatResult = os.stat_result


class AllWatcher:
    def __init__(self, root_path: Path | str, ignored_paths: set[str] | None = None) -> None:
        self.files: dict[str, float] = {}
        self.root_path = str(root_path)
        self.ignored_paths = ignored_paths

    def should_watch_dir(self, entry: DirEntry) -> bool:
        return True

    def should_watch_file(self, entry: DirEntry) -> bool:
        return True

    async def _walk(self, path: str, changes: set[FileChange], new_files: dict[str, float]) -> None:
        if os.path.isfile(path):
            await self._watch_file(path, changes, new_files, os.stat(path))
        else:
            await self._walk_dir(path, changes, new_files)

    async def _watch_file(
        self, path: str, changes: set[FileChange], new_files: dict[str, float], stat: StatResult
    ) -> None:
        mtime = stat.st_mtime
        new_files[path] = mtime
        old_mtime = self.files.get(path)
        if not old_mtime:
            changes.add((Change.added, path))
        elif old_mtime != mtime:
            changes.add((Change.modified, path))

    async def _walk_dir(self, dir_path: str, changes: set[FileChange], new_files: dict[str, float]) -> None:
        for entry in os.scandir(dir_path):
            if self.ignored_paths is not None and os.path.join(dir_path, entry) in self.ignored_paths:
                continue

            try:
                if entry.is_dir():
                    if self.should_watch_dir(entry):
                        await self._walk_dir(entry.path, changes, new_files)
                elif self.should_watch_file(entry):
                    await self._watch_file(entry.path, changes, new_files, entry.stat())
            except FileNotFoundError:  # pragma: no cover
                # sometimes we can't find the file. If it was deleted since
                # `entry` was allocated, then it doesn't matter and can be
                # ignored.  It might also be a bad symlink, in which case we
                # should silently skip it - users don't want to constantly spam
                # warnings, esp if they can't remove the symlink (e.g. from a
                # node_modules directory).
                pass

    async def check(self) -> set[FileChange]:
        changes: set[FileChange] = set()
        new_files: dict[str, float] = {}
        try:
            await self._walk(self.root_path, changes, new_files)
        except OSError as e:
            # check for unexpected errors
            logger.warning('error walking file system: %s %s', e.__class__.__name__, e)

        # look for deleted
        deleted = self.files.keys() - new_files.keys()
        if deleted:
            changes |= {(Change.deleted, entry) for entry in deleted}

        self.files = new_files
        return changes


class DefaultDirWatcher(AllWatcher):
    ignored_dirs = {'.git', '__pycache__', 'site-packages', '.idea', 'node_modules'}

    def should_watch_dir(self, entry: DirEntry) -> bool:
        return entry.name not in self.ignored_dirs


class DefaultWatcher(DefaultDirWatcher):
    ignored_file_regexes = r'\.py[cod]$', r'\.___jb_...___$', r'\.sw.$', '~$', r'^\.\#', r'^flycheck_'

    def __init__(self, root_path: str | Path) -> None:
        self._ignored_file_regexes = tuple(re.compile(r) for r in self.ignored_file_regexes)
        super().__init__(root_path)

    def should_watch_file(self, entry: DirEntry) -> bool:
        return not any(r.search(entry.name) for r in self._ignored_file_regexes)


class PythonWatcher(DefaultDirWatcher):
    def __init__(
        self,
        root_path: Path | str,
        ignored_paths: set[str] | None = None,
        *,
        extra_extensions: tuple[str, ...] = (),
    ) -> None:
        self.extensions = ('.py', '.pyx', '.pyd') + extra_extensions
        super().__init__(root_path, ignored_paths)

    def should_watch_file(self, entry: DirEntry) -> bool:
        return entry.name.endswith(self.extensions)


class RegExpWatcher(AllWatcher):
    def __init__(self, root_path: str | Path, re_files: str | None = None, re_dirs: str | None = None):
        self.re_files: Pattern[str] | None = re.compile(re_files) if re_files is not None else re_files
        self.re_dirs: Pattern[str] | None = re.compile(re_dirs) if re_dirs is not None else re_dirs
        super().__init__(root_path)

    def should_watch_file(self, entry: DirEntry) -> bool:
        if self.re_files is not None:
            return bool(self.re_files.match(entry.path))
        else:
            return super().should_watch_file(entry)

    def should_watch_dir(self, entry: DirEntry) -> bool:
        if self.re_dirs is not None:
            return bool(self.re_dirs.match(entry.path))
        else:
            return super().should_watch_dir(entry)
