from __future__ import annotations

from typer import Typer

CLI_APP = Typer(no_args_is_help=True)

try:
    # This command requires "baxter.high_level.db", which might
    # not be available.
    from ._db_cmd import DB_CMD

except ImportError:
    pass
else:
    CLI_APP.add_typer(DB_CMD)

try:
    # This command requires "baxter.high_level", which might not
    # be available.
    from ._snipify import snipify
except ImportError:
    pass
else:
    CLI_APP.command()(snipify)
