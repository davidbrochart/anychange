import os
from pathlib import Path
from typing import Dict, Union

import pytest

PathDict = Dict[str, Union['PathDict', str, bytes]]


def mktree(root_dir: Path, path_dict: PathDict):
    """
    Create a tree of files from a dictionary of name > content lookups.
    """
    for name, content in path_dict.items():
        path = root_dir / name

        if isinstance(content, dict):
            path.mkdir(parents=True, exist_ok=True)
            mktree(path, content)
        elif isinstance(content, str):
            path.write_text(content)
        else:  # pragma: nocover
            assert isinstance(content, bytes), 'content must be a dict, str or bytes'
            path.write_bytes(content)
