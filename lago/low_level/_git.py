import logging
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_GIT_LOGGER = logging.getLogger("git")


@dataclass(frozen=True, kw_only=True)
class Git:
    """Git micro-client."""

    directory: Path

    def clone(self, repo: str) -> None:
        self._debug("Git clone")
        self._run("clone", repo, str(self.directory), specify_dir=False)

    def install_lfs(self) -> None:
        """Install git-lfs hooks in the repository."""
        self._debug("Install LFS hooks")
        self._run("lfs", "install")

    def fetch_lfs(self, *, include_paths: Sequence[Path] | None = None) -> None:
        self._debug("Fetch LFS objects (include_paths=%s)", include_paths)
        cmd: list[str] = ["lfs", "fetch"]
        if include_paths is not None:
            cmd.append("--include")
            cmd.extend(str(path) for path in include_paths)
        self._run(*cmd)

    def checkout_lfs(self) -> None:
        self._debug("Checkout LFS objects")
        self._run("lfs", "checkout")

    def raise_if_git_lfs_is_missing(self) -> None:
        self._debug("Check if `git-lfs` is installed")
        try:
            self._run("lfs", stdout=subprocess.DEVNULL)
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
