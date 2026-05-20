import logging
import shutil
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

from filelock import FileLock

from ._git import Git
from ._lago_cache import setup_and_get_lago_cache_dir
from ._lago_constants import PRIVATE_ASSETS_GIT_URL

_LOGGER = logging.getLogger(__name__)


@cache
def setup_and_get_assets_dir(
    *,
    commit_id: str,
    git_url: str | None = None,
) -> Path:
    """Return a worktree of SBT's private assets pinned at ``commit_id``.

    Multiple commits can be checked out side-by-side. All checkouts of the same
    ``git_url`` share a single bare clone, so the LFS blob store under
    ``.git/lfs/objects/`` is shared too: a given LFS blob is downloaded at most
    once per content hash regardless of how many commits reference it.

    Layout under the lago cache directory::

        <cache>/<repo>.git/                  # shared bare clone + LFS store
        <cache>/<repo>.git.ongoing           # present while the store is being set up
        <cache>/<repo>--<commit_id>/         # worktree at <commit_id>
        <cache>/<repo>--<commit_id>.ongoing  # present while a worktree is being checked out
        <cache>/<repo>.lock                  # per-git_url FileLock

    Both ``.ongoing`` flags are created before their respective heavy step and
    removed only on success. If a process crashes the flag survives, and the
    next call cleans up the partial artifact and retries.

    Raises ``RuntimeError`` if the ``git-lfs`` extension is not available.
    """
    if git_url is None:
        git_url = PRIVATE_ASSETS_GIT_URL

    cache_dir = setup_and_get_lago_cache_dir()
    repo_name = Path(urlparse(git_url).path).stem

    store_dir = cache_dir / f"{repo_name}.git"
    store_ongoing_flag = cache_dir / f"{repo_name}.git.ongoing"
    worktree_dir = cache_dir / f"{repo_name}--{commit_id}"
    worktree_ongoing_flag = cache_dir / f"{repo_name}--{commit_id}.ongoing"
    lock_file = cache_dir / f"{repo_name}.lock"

    # Per-git_url lock so concurrent processes (e.g., pytest-xdist workers)
    # don't race on the shared store or on the same worktree.
    with FileLock(lock_file):
        if worktree_dir.exists() and not worktree_ongoing_flag.exists():
            _LOGGER.debug("Reusing worktree at %s", worktree_dir)
            return worktree_dir

        if worktree_dir.exists():
            _LOGGER.info("Removing partial worktree at %s", worktree_dir)
            shutil.rmtree(worktree_dir)
        worktree_ongoing_flag.unlink(missing_ok=True)

        store_git = Git(directory=store_dir)
        store_git.raise_if_git_lfs_is_missing()

        if not store_dir.exists() or store_ongoing_flag.exists():
            if store_dir.exists():
                _LOGGER.info("Removing partial bare store at %s", store_dir)
                shutil.rmtree(store_dir)
            store_ongoing_flag.touch()
            store_git.clone_bare(git_url)
            store_git.install_lfs()
            store_ongoing_flag.unlink()

        store_git.fetch_commit(commit_id)
        store_git.fetch_lfs_for_commit(commit_id)

        worktree_ongoing_flag.touch()
        store_git.prune_worktrees()
        store_git.add_worktree(path=worktree_dir, commit_id=commit_id)
        Git(directory=worktree_dir).checkout_lfs()
        worktree_ongoing_flag.unlink()

        return worktree_dir
