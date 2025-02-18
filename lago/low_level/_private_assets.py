import logging
from collections.abc import Sequence
from functools import cache
from pathlib import Path

from filelock import FileLock

from ._git import Git
from ._lago_cache import setup_and_get_lago_cache_dir
from ._lago_constants import (
    PRIVATE_ASSETS_DIR_NAME,
    PRIVATE_ASSETS_GIT_URL,
    PRIVATE_ASSETS_LOCK_FILE_NAME,
)

_LOGGER = logging.getLogger(__name__)


@cache
def setup_and_get_private_assets_dir(
    *,
    include_paths: Sequence[Path] | None = None,
    stop_if_not_empty: bool | None = None,
) -> Path:
    """Return the directory that contains SBT's private assets.

    This is a one-stop function. It does everything to set up the private assets
    directory for you. That includes:

     * Clone the `private-assets` git repository (or use the submodule if available)
     * Install git-lfs (Git Large File Storage)
     * Fetch and checkout the requested assets

    These are some heavy steps that make take a long while. Therefore, the very first
    call to this function (in a freshly checked out repository) may be slow. Subsequent
    calls to this function, however, is essentially a no-op.

    Raises `RuntimeError` if the `git-lfs` extension is not available.


    ## `git status` says that the files are modified

    This is normal. This is just how `git status` and the `git-lfs` extension
    interacts. When we do `git lfs checkout` it replaces the local pointer
    file with the actual content found on the remote LFS server. Git sees this
    as a change (pointer changed to content). That's just how it is.

    Get back the pointers with this command:

        git reset --hard HEAD

    Note that this undoes *all* changes in the current repository. Not just the
    pointer-to-content changes.
    """
    if stop_if_not_empty is None:
        stop_if_not_empty = True

    cache_dir = setup_and_get_lago_cache_dir()

    # This lock ensures that only a single process modifies the `private-assets`
    # at a time. This is especially relevant for test suites that use `pytest-xdist`.
    lock_file = cache_dir / PRIVATE_ASSETS_LOCK_FILE_NAME
    with FileLock(lock_file):
        # This is the usual path. Examples:
        #
        #     "~/projects/baxter/.lago_cache/private-assets"
        #     "[...] workspace/sources/python3-lago/.lago_cache/private-assets"
        #
        # ruff: noqa: ERA001
        private_assets_dir = cache_dir / PRIVATE_ASSETS_DIR_NAME

        # Early out if the `private-assets` directory is not empty.
        # Use this to, e.g., speed up this function call on subsequent invocations.
        if stop_if_not_empty and (
            private_assets_dir.exists() and not _is_dir_empty(private_assets_dir)
        ):
            _LOGGER.debug(
                "The '%s' directory is not empty. "
                "We assume that it contains the latest version and stop early.",
                private_assets_dir.name,
            )
            return private_assets_dir

        assets_git = Git(directory=private_assets_dir)
        assets_git.clone(PRIVATE_ASSETS_GIT_URL)

        assets_git.raise_if_git_lfs_is_missing()
        assets_git.install_lfs()
        assets_git.fetch_lfs(include_paths=include_paths)
        assets_git.checkout_lfs()
        return private_assets_dir


def _is_dir_empty(directory: Path) -> bool:
    for _ in directory.iterdir():
        return False
    return True
