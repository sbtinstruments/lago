from pathlib import Path

from ._lago_constants import LAGO_CACHE_DIR_NAME
from ._project_dir import get_project_dir


def setup_and_get_lago_cache_dir() -> Path:
    # We assume that you call this function within the context of a
    # git repository. We call this the "project" (it could be, e.g., baxter,
    # mester, lago, etc.).
    project_dir = get_project_dir()
    cache_dir = project_dir / LAGO_CACHE_DIR_NAME
    cache_dir.mkdir(exist_ok=True)
    return cache_dir
