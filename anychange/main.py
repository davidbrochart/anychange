from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any

import anyio

from .watcher import DefaultWatcher

__all__ = 'awatch'
logger = logging.getLogger('anychange.main')

if TYPE_CHECKING:


    from .watcher import AllWatcher, FileChange

    FileChanges = set[FileChange]
    AnyCallable = Callable[..., Any]


def unix_ms() -> int:
    return int(round(time() * 1000))


class awatch:
    """
    asynchronous equivalent of watch using a threaded executor.

    3.5 doesn't support yield in coroutines so we need all this fluff. Yawwwwn.
    """

    __slots__ = (
        '_path',
        '_watcher_cls',
        '_watcher_kwargs',
        '_debounce',
        '_min_sleep',
        '_stop_event',
        '_normal_sleep',
        '_w',
        'lock',
    )

    def __init__(
        self,
        path: Path | str,
        *,
        watcher_cls: type[AllWatcher] = DefaultWatcher,
        watcher_kwargs: dict[str, Any] | None = None,
        debounce: int = 1600,
        normal_sleep: int = 400,
        min_sleep: int = 50,
        stop_event: anyio.Event | None = None,
    ) -> None:
        self._path = path
        self._watcher_cls = watcher_cls
        self._watcher_kwargs = watcher_kwargs or dict()
        self._debounce = debounce
        self._normal_sleep = normal_sleep
        self._min_sleep = min_sleep
        self._stop_event = stop_event
        self._w: AllWatcher | None = None
        self.lock = anyio.Lock()

    def __aiter__(self) -> awatch:
        return self

    async def __anext__(self) -> FileChanges:
        if self._w:
            watcher = self._w
        else:
            watcher = self._w = self._watcher_cls(self._path, **self._watcher_kwargs)
        check_time = 0
        changes: FileChanges = set()
        last_change = 0
        while True:
            if self._stop_event and self._stop_event.is_set():
                raise StopAsyncIteration()
            async with self.lock:
                if not changes:
                    last_change = unix_ms()

                if check_time:  # pragma: nocover
                    if changes:
                        sleep_time = self._min_sleep
                    else:
                        sleep_time = max(self._normal_sleep - check_time, self._min_sleep)
                    await anyio.sleep(sleep_time / 1000)

                s = unix_ms()
                new_changes = await watcher.check()
                changes.update(new_changes)
                now = unix_ms()
                check_time = now - s
                debounced = now - last_change
                if logger.isEnabledFor(logging.DEBUG) and changes:
                    logger.debug(
                        '%s time=%0.0fms debounced=%0.0fms files=%d changes=%d (%d)',
                        self._path,
                        check_time,
                        debounced,
                        len(watcher.files),
                        len(changes),
                        len(new_changes),
                    )

                if changes and (not new_changes or debounced > self._debounce):
                    logger.debug('%s changes released debounced=%0.0fms', self._path, debounced)
                    return changes
