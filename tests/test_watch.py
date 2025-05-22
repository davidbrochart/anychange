import re
import sys
import threading
from pathlib import Path
from time import sleep

import anyio
import pytest

from anychange import AllWatcher, Change, DefaultWatcher, PythonWatcher, RegExpWatcher, awatch

from .conftest import mktree

pytestmark = pytest.mark.anyio
skip_on_windows = pytest.mark.skipif(sys.platform == 'win32', reason='fails on windows')
skip_unless_linux = pytest.mark.skipif(sys.platform != 'linux', reason='test only on linux')
tree = {
    'foo': {
        'bar.txt': 'bar',
        'spam.py': 'whatever',
        'spam.pyc': 'splosh',
        'recursive_dir': {
            'a.js': 'boom',
        },
        '.git': {
            'x': 'y',
        },
    }
}


async def test_add(tmp_path):
    watcher = AllWatcher(tmp_path)
    changes = await watcher.check()
    assert changes == set()

    sleep(0.01)
    (tmp_path / 'foo.txt').write_text('foobar')

    changes = await watcher.check()
    assert changes == {(Change.added, str((tmp_path / 'foo.txt')))}


async def test_add_watched_file(tmp_path):
    file = tmp_path / 'bar.txt'

    watcher = AllWatcher(file)
    assert await watcher.check() == set()

    sleep(0.01)
    file.write_text('foobar')
    assert await watcher.check() == {(Change.added, str(file))}


async def test_modify(tmp_path: Path):
    mktree(tmp_path, tree)

    watcher = AllWatcher(tmp_path)
    await watcher.check()
    assert await watcher.check() == set()

    sleep(0.01)
    (tmp_path / 'foo/bar.txt').write_text('foobar')

    assert await watcher.check() == {(Change.modified, str(tmp_path / 'foo/bar.txt'))}


@skip_on_windows
async def test_ignore_root(tmp_path):
    mktree(tmp_path, tree)
    watcher = AllWatcher(tmp_path, ignored_paths={str(tmp_path / 'foo')})
    await watcher.check()

    assert await watcher.check() == set()

    sleep(0.01)
    (tmp_path / 'foo/bar.txt').write_text('foobar')

    assert await watcher.check() == set()


@skip_on_windows
async def test_ignore_file_path(tmp_path):
    mktree(tmp_path, tree)
    watcher = AllWatcher(tmp_path, ignored_paths={str(tmp_path / 'foo' / 'bar.txt')})
    await watcher.check()

    assert await watcher.check() == set()

    sleep(0.01)
    (tmp_path / 'foo' / 'bar.txt').write_text('foobar')
    (tmp_path / 'foo' / 'new_not_ignored.txt').write_text('foobar')
    (tmp_path / 'foo' / 'spam.py').write_text('foobar')

    assert await watcher.check() == {
        (Change.added, str(tmp_path / 'foo' / 'new_not_ignored.txt')),
        (Change.modified, str(tmp_path / 'foo' / 'spam.py')),
    }


@skip_on_windows
async def test_ignore_subdir(tmp_path):
    mktree(tmp_path, tree)
    watcher = AllWatcher(tmp_path, ignored_paths={str(tmp_path / 'dir' / 'ignored')})
    await watcher.check()
    assert await watcher.check() == set()

    sleep(0.01)
    (tmp_path / 'dir').mkdir()
    (tmp_path / 'dir' / 'ignored').mkdir()
    (tmp_path / 'dir' / 'not_ignored').mkdir()

    (tmp_path / 'dir' / 'ignored' / 'file.txt').write_text('content')
    (tmp_path / 'dir' / 'not_ignored' / 'file.txt').write_text('content')

    assert await watcher.check() == {(Change.added, str(tmp_path / 'dir' / 'not_ignored' / 'file.txt'))}


async def test_modify_watched_file(tmp_path):
    file = tmp_path / 'bar.txt'
    file.write_text('foobar')

    watcher = AllWatcher(file)
    await watcher.check()
    assert await watcher.check() == set()

    sleep(0.01)
    file.write_text('foobar')
    assert await watcher.check() == {(Change.modified, str(file))}  # same content but time updated

    sleep(0.01)
    file.write_text('baz')
    assert await watcher.check() == {(Change.modified, str(file))}


async def test_delete(tmp_path):
    mktree(tmp_path, tree)

    watcher = AllWatcher(tmp_path)
    await watcher.check()

    sleep(0.01)
    (tmp_path / 'foo/bar.txt').unlink()

    assert await watcher.check() == {(Change.deleted, str((tmp_path / 'foo/bar.txt')))}


async def test_delete_watched_file(tmp_path):
    file = tmp_path / 'bar.txt'
    file.write_text('foobar')

    watcher = AllWatcher(file)
    await watcher.check()
    assert await watcher.check() == set()

    sleep(0.01)
    file.unlink()
    assert await watcher.check() == {(Change.deleted, str(file))}


async def test_ignore_file(tmp_path):
    mktree(tmp_path, tree)

    watcher = DefaultWatcher(tmp_path)
    await watcher.check()

    sleep(0.01)
    (tmp_path / 'foo/spam.pyc').write_text('foobar')

    assert await watcher.check() == set()


async def test_ignore_dir(tmp_path):
    mktree(tmp_path, tree)

    watcher = DefaultWatcher(tmp_path)
    await watcher.check()

    sleep(0.01)
    (tmp_path / 'foo/.git/abc').write_text('xxx')

    assert await watcher.check() == set()


async def test_python(tmp_path):
    mktree(tmp_path, tree)

    watcher = PythonWatcher(tmp_path)
    await watcher.check()

    sleep(0.01)
    (tmp_path / 'foo/spam.py').write_text('xxx')
    (tmp_path / 'foo/bar.txt').write_text('xxx')
    (tmp_path / 'foo/spam.md').write_text('xxx')

    assert await watcher.check() == {(Change.modified, str(tmp_path / 'foo/spam.py'))}


async def test_python_extensions(tmp_path):
    mktree(tmp_path, tree)

    watcher = PythonWatcher(tmp_path, extra_extensions=('.md',))
    await watcher.check()

    sleep(0.01)
    (tmp_path / 'foo/spam.py').write_text('xxx')
    (tmp_path / 'foo/bar.txt').write_text('xxx')
    (tmp_path / 'foo/spam.md').write_text('xxx')

    assert await watcher.check() == {
        (Change.modified, str(tmp_path / 'foo/spam.py')),
        (Change.added, str(tmp_path / 'foo/spam.md')),
    }


async def test_regexp(tmp_path):
    mktree(tmp_path, tree)

    re_files = r'^.*(\.txt|\.js)$'
    re_dirs = r'^(?:(?!recursive_dir).)*$'

    watcher = RegExpWatcher(tmp_path, re_files, re_dirs)
    await watcher.check()
    changes = await watcher.check()
    assert changes == set()

    sleep(0.01)
    (tmp_path / 'foo/spam.py').write_text('xxx')
    (tmp_path / 'foo/bar.txt').write_text('change')
    (tmp_path / 'foo/borec.txt').write_text('ahoy')
    (tmp_path / 'foo/borec-js.js').write_text('peace')
    (tmp_path / 'foo/recursive_dir/b.js').write_text('borec')

    assert await watcher.check() == {
        (Change.modified, str((tmp_path / 'foo/bar.txt'))),
        (Change.added, str((tmp_path / 'foo/borec.txt'))),
        (Change.added, str((tmp_path / 'foo/borec-js.js'))),
    }


async def test_regexp_no_re_dirs(tmp_path):
    mktree(tmp_path, tree)

    re_files = r'^.*(\.txt|\.js)$'

    watcher_no_re_dirs = RegExpWatcher(tmp_path, re_files)
    await watcher_no_re_dirs.check()
    changes = await watcher_no_re_dirs.check()
    assert changes == set()

    sleep(0.01)
    (tmp_path / 'foo/spam.py').write_text('xxx')
    (tmp_path / 'foo/bar.txt').write_text('change')
    (tmp_path / 'foo/recursive_dir/foo.js').write_text('change')

    assert await watcher_no_re_dirs.check() == {
        (Change.modified, str((tmp_path / 'foo/bar.txt'))),
        (Change.added, str((tmp_path / 'foo/recursive_dir/foo.js'))),
    }


async def test_regexp_no_re_files(tmp_path):
    mktree(tmp_path, tree)

    re_dirs = r'^(?:(?!recursive_dir).)*$'

    watcher_no_re_files = RegExpWatcher(tmp_path, re_dirs=re_dirs)
    await watcher_no_re_files.check()
    changes = await watcher_no_re_files.check()
    assert changes == set()

    sleep(0.01)
    (tmp_path / 'foo/spam.py').write_text('xxx')
    (tmp_path / 'foo/bar.txt').write_text('change')
    (tmp_path / 'foo/recursive_dir/foo.js').write_text('change')

    assert await watcher_no_re_files.check() == {
        (Change.modified, str((tmp_path / 'foo/spam.py'))),
        (Change.modified, str((tmp_path / 'foo/bar.txt'))),
    }


async def test_regexp_no_args(tmp_path):
    mktree(tmp_path, tree)

    watcher_no_args = RegExpWatcher(tmp_path)
    await watcher_no_args.check()
    changes = await watcher_no_args.check()
    assert changes == set()

    sleep(0.01)
    (tmp_path / 'foo/spam.py').write_text('xxx')
    (tmp_path / 'foo/bar.txt').write_text('change')
    (tmp_path / 'foo/recursive_dir/foo.js').write_text('change')

    assert await watcher_no_args.check() == {
        (Change.modified, str((tmp_path / 'foo/spam.py'))),
        (Change.modified, str((tmp_path / 'foo/bar.txt'))),
        (Change.added, str((tmp_path / 'foo/recursive_dir/foo.js'))),
    }


@skip_on_windows
async def test_does_not_exist(caplog, tmp_path):
    p = tmp_path / 'missing'
    watcher = AllWatcher(p)
    await watcher.check()
    assert f"error walking file system: FileNotFoundError [Errno 2] No such file or directory: '{p}'" in caplog.text


async def test_watch_watcher_kwargs(mocker):
    class FakeWatcher:
        def __init__(self, path, arg1=None, arg2=None):
            self._results = iter(
                [
                    {arg1},
                    set(),
                    {arg2},
                    set(),
                ]
            )

        async def check(self):
            return next(self._results)

    kwargs = dict(arg1='foo', arg2='bar')

    ans = []
    async for v in awatch('xxx', watcher_cls=FakeWatcher, watcher_kwargs=kwargs, debounce=5, normal_sleep=2, min_sleep=1):
        print(v)
        ans.append(v)
        if len(ans) == 2:
            break
    assert ans == [{kwargs['arg1']}, {kwargs['arg2']}]


async def test_awatch(mocker):
    class FakeWatcher:
        def __init__(self, path):
            self._results = iter(
                [
                    set(),
                    set(),
                    {'r1'},
                    set(),
                    {'r2'},
                    set(),
                ]
            )

        async def check(self):
            return next(self._results)

    ans = []
    async for v in awatch('xxx', watcher_cls=FakeWatcher, debounce=5, normal_sleep=2, min_sleep=1):
        ans.append(v)
        if len(ans) == 2:
            break
    assert ans == [{'r1'}, {'r2'}]


async def test_awatch_stop():
    class FakeWatcher:
        def __init__(self, path):
            self._results = iter(
                [
                    {'r1'},
                    set(),
                    {'r2'},
                ]
            )

    stop_event = anyio.Event()
    stop_event.set()
    async for v in awatch('xxx', watcher_cls=FakeWatcher, debounce=5, min_sleep=1, stop_event=stop_event):
        pass  # pragma: nocover


@skip_unless_linux
async def test_awatch_log(mocker, caplog):
    mock_log_enabled = mocker.patch('anychange.main.logger.isEnabledFor')
    mock_log_enabled.return_value = True

    class FakeWatcher:
        def __init__(self, path):
            self.files = [1, 2, 3]

        async def check(self):
            return {'r1'}

    async for v in awatch('xxx', watcher_cls=FakeWatcher, debounce=5, min_sleep=1):
        assert v == {'r1'}
        break

    print(caplog.text)
    assert caplog.text.count('DEBUG') > 3
    assert 'xxx time=Xms debounced=Xms files=3 changes=1 (1)' in re.sub(r'\dms', 'Xms', caplog.text)
