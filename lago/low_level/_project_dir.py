import subprocess
from functools import cache
from pathlib import Path


@cache
def get_project_dir() -> Path:
    cmd: tuple[str, ...] = ("git", "rev-parse", "--show-toplevel")
    completed = subprocess.run(  # noqa: S603
        cmd,
        stdout=subprocess.PIPE,
        encoding="utf8",
        check=True,
    )
    return Path(completed.stdout.strip())
