import sys

import pytest

from anychange import arun_process, run_process
from anychange.main import _start_process


class FakeWatcher:
    def __init__(self, path):
        self._async = 'async' in path
        self._check = 0
        self.files = [1, 2, 3]

    def check(self):
        self._check += 1
        if self._check == 1:
            return {'x'}
        elif self._check == 2:
            return set()
        elif self._async:
            raise StopAsyncIteration
        else:
            raise KeyboardInterrupt


class FakeProcess:
    def __init__(self, is_alive=True, exitcode=1, pid=123):
        self._is_alive = is_alive
        self.exitcode = exitcode
        self.pid = pid

    def is_alive(self):
        return self._is_alive

    def join(self, wait):
        pass


def test_alive_terminates(mocker):
    mock_start_process = mocker.patch('anychange.main._start_process')
    mock_start_process.return_value = FakeProcess()
    mock_kill = mocker.patch('anychange.main.os.kill')

    assert run_process('/x/y/z', object(), watcher_cls=FakeWatcher, debounce=5, min_sleep=1) == 1
    assert mock_start_process.call_count == 2
    assert mock_kill.call_count == 2  # kill in loop + final kill


def test_dead_callback(mocker):
    mock_start_process = mocker.patch('anychange.main._start_process')
    mock_start_process.return_value = FakeProcess(is_alive=False)
    mock_kill = mocker.patch('anychange.main.os.kill')
    c = mocker.MagicMock()

    assert run_process('/x/y/z', object(), watcher_cls=FakeWatcher, callback=c, debounce=5, min_sleep=1) == 1
    assert mock_start_process.call_count == 2
    assert mock_kill.call_count == 0
    assert c.call_count == 1
    c.assert_called_with({'x'})


@pytest.mark.skipif(sys.platform == 'win32', reason='fails on windows')
def test_alive_doesnt_terminate(mocker):
    mock_start_process = mocker.patch('anychange.main._start_process')
    mock_start_process.return_value = FakeProcess(exitcode=None)
    mock_kill = mocker.patch('anychange.main.os.kill')

    assert run_process('/x/y/z', object(), watcher_cls=FakeWatcher, debounce=5, min_sleep=1) == 1
    assert mock_start_process.call_count == 2
    assert mock_kill.call_count == 4  # 2 kills in loop (graceful and termination) + 2 final kills


def test_start_process(mocker):
    mock_process = mocker.patch('anychange.main.spawn_context.Process')
    v = object()
    _start_process(v, (1, 2, 3), {})
    assert mock_process.call_count == 1
    mock_process.assert_called_with(target=v, args=(1, 2, 3), kwargs={})


@pytest.mark.skipif(sys.version_info < (3, 8), reason='AsyncMock unavailable')
async def test_async_alive_terminates(mocker):
    mock_start_process = mocker.patch('anychange.main._start_process')
    mock_start_process.return_value = FakeProcess()
    mock_kill = mocker.patch('anychange.main.os.kill')
    c = mocker.AsyncMock(return_value=1)

    reloads = await arun_process('/x/y/async', object(), watcher_cls=FakeWatcher, callback=c, debounce=5, min_sleep=1)
    assert reloads == 1
    assert mock_start_process.call_count == 2
    assert mock_kill.call_count == 2  # kill in loop + final kill
    assert c.call_count == 1
    c.assert_called_with({'x'})
