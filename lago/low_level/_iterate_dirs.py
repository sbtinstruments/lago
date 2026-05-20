from collections.abc import Iterable
from pathlib import Path

from ._lago_constants import PRIVATE_ASSETS_COMMIT
from ._setup_and_get_assets_dir import setup_and_get_assets_dir


def get_record_dirs() -> Iterable[Path]:
    private_assets = setup_and_get_assets_dir(commit_id=PRIVATE_ASSETS_COMMIT)
    executions_dir = private_assets / "executions"
    for execution_dir in executions_dir.iterdir():
        if not execution_dir.is_dir():
            continue
        yield execution_dir
