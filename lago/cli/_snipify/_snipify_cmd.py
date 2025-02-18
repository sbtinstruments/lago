from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Annotated

import rich
import typer
from baxter.high_level import Miscellaneous
from cyto.model import FrozenModel
from pydantic import FilePath
from rich.prompt import Confirm
from typer import Typer

from ...low_level import setup_and_get_private_assets_dir
from ._component_qc_template import RAW_DATA_FILE_NAME, ComponentQcTemplate

# SNIPIFY_CMD = Typer(
#     name="snipify",
#     help="Convert device data dumps into the snip format.",
#     no_args_is_help=True,
# )

_MANIFEST = """
{
    "extensionToMediaType": {
        ".json": "application/vnd.sbt.measurement-report+json",
        ".msc.json": "application/vnd.sbt.misc+json"
    },
    "pathToMediaType": {
        "attributes.json": "application/vnd.sbt.snip.attributes+json"
    }
}
"""


def snipify(
    raw_data_dir: Annotated[
        Path, typer.Argument(dir_okay=True, file_okay=False, exists=True)
    ],
    yes_to_all: Annotated[bool, typer.Option("-y", is_flag=True)] = False,
    replace_existing: Annotated[bool, typer.Option(is_flag=True)] = False,
    skip_empty: Annotated[bool, typer.Option(is_flag=True)] = True,
    miscellaneous_file: Annotated[Path | None, typer.Option()] = None,
    component_qc_template_path: Annotated[Path | None, typer.Option()] = None,
) -> None:
    if miscellaneous_file is not None:
        miscellaneous_text = miscellaneous_file.read_text(encoding="utf8")
        miscellaneous = Miscellaneous.model_validate_json(miscellaneous_text)
    else:
        miscellaneous = None

    component_qc_template = None
    if component_qc_template_path is not None:
        component_qc_template_text = component_qc_template_path.read_text(
            encoding="utf8"
        )
        component_qc_template = ComponentQcTemplate.model_validate_json(
            component_qc_template_text
        )

    to_convert: list[RawDataFileSet] = []
    all_iqs_files = (
        entry
        for entry in raw_data_dir.glob("*.iqs")
        if entry.is_file() and entry.suffixes != [".fragments", ".iqs"]
    )

    if component_qc_template is not None:
        all_iqs_files = tuple(all_iqs_files)
        component_qc_template.validate_files(all_iqs_files)
        all_iqs_files = (
            iqs_file
            for iqs_file in all_iqs_files
            if component_qc_template.check_file_belongs_to(iqs_file)
        )

    for iqs_file in all_iqs_files:
        if component_qc_template is not None:
            if miscellaneous is not None:
                raise ValueError(
                    "You can not specify both a miscellaneous file and a "
                    "component QC template at the same time."
                )
            miscellaneous = component_qc_template.get_miscellaneous_from_file(iqs_file)
        try:
            file_set = RawDataFileSet.from_file(iqs_file, miscellaneous=miscellaneous)
        except ValueError as exc:
            rich.print(f"We skip '{iqs_file.name}' due to: {exc}")
            continue

        if skip_empty and iqs_file.stat().st_size == 0:
            rich.print(f"We skip '{iqs_file.name}' because it is empty")
            continue

        to_convert.append(file_set)

    rich.print(f"Found {len(to_convert)} entries to snipify")
    if not yes_to_all and not Confirm.ask("Continue?"):
        sys.exit()

    private_assets = setup_and_get_private_assets_dir()
    executions_dir = private_assets / "executions"

    rich.print(f"We put the results in: {executions_dir}")

    for file_set in to_convert:
        try:
            file_set.save_as_snip(executions_dir, replace_existing_dir=replace_existing)
        except Exception as exc:
            rich.print(f"Error for {file_set.iqs.stem} due to: {exc}")


class RawDataFileSet(FrozenModel):
    hostname: str
    raw_datetime: str
    iqs: FilePath
    bdr: FilePath
    csv: FilePath
    json_report: FilePath
    miscellaneous: Miscellaneous = Miscellaneous()

    def save_as_snip(
        self, parent_directory: Path, *, replace_existing_dir: bool | None = None
    ) -> None:
        if replace_existing_dir is None:
            replace_existing_dir = False

        snip_name = f"{self.hostname}-{self.raw_datetime}"
        snip_dir = parent_directory / f"{snip_name}.snip"

        if replace_existing_dir:
            shutil.rmtree(snip_dir, ignore_errors=True)
            snip_dir.mkdir()
        else:
            snip_dir.mkdir(exist_ok=True)
            if list(snip_dir.iterdir()):
                raise RuntimeError(f"Snip directory not empty: {snip_dir}")

        attributes_file = snip_dir / "attributes.json"
        attributes_file.write_text("{}", encoding="utf8")

        manifest_file = snip_dir / "manifest.json"
        manifest_file.write_text(_MANIFEST, encoding="utf8")

        data_dir = snip_dir / "data"
        data_dir.mkdir(exist_ok=True)

        shutil.copyfile(self.iqs, data_dir / self.iqs.name)
        shutil.copyfile(self.bdr, data_dir / self.bdr.name)
        shutil.copyfile(self.csv, data_dir / self.csv.name)
        shutil.copyfile(self.json_report, data_dir / self.json_report.name)

        miscellaneous_file = data_dir / "metadata.msc.json"
        miscellaneous_file.write_text(
            self.miscellaneous.model_dump_json(), encoding="utf8"
        )

    @classmethod
    def from_file(
        cls, file: Path, *, miscellaneous: Miscellaneous | None = None
    ) -> RawDataFileSet:
        if miscellaneous is None:
            miscellaneous = Miscellaneous()
        matches = RAW_DATA_FILE_NAME.match(file.name)
        if matches is None:
            raise ValueError("Invalid file name for raw data set")
        hostname = matches.group("hostname")
        date = matches.group("date")
        time = matches.group("time")
        raw_datetime = f"{date}-{time}"

        iqs = file.with_suffix(".iqs")
        bdr = file.with_suffix(".bdr")
        csv = file.with_suffix(".csv")
        json_report = file.with_suffix(".json")
        return cls(
            hostname=hostname,
            raw_datetime=raw_datetime,
            iqs=iqs,
            bdr=bdr,
            csv=csv,
            json_report=json_report,
            miscellaneous=miscellaneous,
        )
