import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_GIT_LOGGER = logging.getLogger("git")


@dataclass(frozen=True, kw_only=True)
class Git:
    """Git micro-client."""

    directory: Path

    def clone_bare(self, repo: str) -> None:
        self._debug("Git clone --bare")
        self._run("clone", "--bare", repo, str(self.directory), specify_dir=False)

    def fetch_commit(self, commit_id: str) -> None:
        self._debug("Fetch commit %s", commit_id)
        self._run("fetch", "origin", commit_id)

    def install_lfs(self) -> None:
        """Install git-lfs hooks/filters in the repository."""
        self._debug("Install LFS hooks")
        self._run("lfs", "install", "--local")

    def fetch_lfs_for_commit(self, commit_id: str) -> None:
        self._debug("Fetch LFS objects for %s", commit_id)
        self._run("lfs", "fetch", "origin", commit_id)

    def checkout_lfs(self) -> None:
        self._debug("Checkout LFS objects")
        self._run("lfs", "checkout")

    def add_worktree(self, *, path: Path, commit_id: str) -> None:
        self._debug("Add worktree %s @ %s", path, commit_id)
        self._run("worktree", "add", "--detach", str(path), commit_id)

    def prune_worktrees(self) -> None:
        self._debug("Prune worktrees")
        self._run("worktree", "prune")

    def raise_if_git_lfs_is_missing(self) -> None:
        self._debug("Check if `git-lfs` is installed")
        try:
            self._run("lfs", stdout=subprocess.DEVNULL, specify_dir=False)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "Install 'git-lfs' (Git Large File Storage) first. "
                "Do so with this command: 'sudo apt update && sudo apt install git-lfs'"
            ) from exc

    def setup_submodule(self, submodule_name: str) -> None:
        self._run("submodule", "update", "--init", submodule_name)

    def _run(
        self,
        *cmd: str,
        specify_dir: bool | None = None,
        stdout: Any = None,
        stderr: Any = None,
    ) -> None:
        if stdout is None:
            stdout = sys.stdout
        if stderr is None:
            stderr = sys.stderr
        if specify_dir is None:
            specify_dir = True
        run_cmd: list[str] = ["git"]
        if specify_dir:
            run_cmd.extend(("-C", str(self.directory)))
        run_cmd.extend(cmd)
        self._debug("run: '%s'", run_cmd)
        subprocess.run(  # noqa: S603
            run_cmd,
            # Output directly so that we get live progress reports
            stdout=stdout,
            stderr=stderr,
            encoding="utf8",
            check=True,
        )

    def _debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        extra = {"directory": self.directory.name}
        _GIT_LOGGER.debug(message, *args, extra=extra, **kwargs)
