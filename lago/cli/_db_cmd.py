import polars as pl
from baxter.high_level.db import Session, create_engine
from rich import print  # noqa: A004
from typer import Option, Typer

DB_CMD = Typer(
    name="db",
    help="Interact with the lago database.",
    no_args_is_help=True,
)


@DB_CMD.command()
def recreate(print_summary: bool = Option(default=True, is_flag=True)) -> None:
    engine = create_engine(recreate_policy="always")
    with Session(bind=engine) as session, session.begin():
        if print_summary:
            _print_summary(session)


@DB_CMD.command()
def summary() -> None:
    with Session() as session, session.begin():
        _print_summary(session)


def _print_summary(session: Session) -> None:
    query = "SELECT * FROM measurement_record"
    print(pl.read_database(query=query, connection=session))
