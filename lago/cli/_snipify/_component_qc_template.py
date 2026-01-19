import re
from collections.abc import Iterator
from pathlib import Path

from baxter.high_level import ComponentQc, Miscellaneous
from cyto.model import FrozenModel
from green_mango.outcome import Liquid, Pbs, SilicaBeadsInPbs

RAW_DATA_FILE_NAME = re.compile(
    r"(?P<prefix>[\w\d]*)-(?P<hostname>[\w\d]{9})-(?P<date>[\d]{8})-(?P<time>[\d]{6})-(?P<mnemonic_id>[\w\d]+)"
)


def validate_file_name(file: Path) -> re.Match[str]:
    matches = RAW_DATA_FILE_NAME.match(file.name)
    if matches is None:
        raise RuntimeError(f"File name '{file.name}' does not match expected pattern")
    return matches


class ComponentQcTemplate(FrozenModel):
    identifier: str
    operator: str
    maintenance_procedure: str
    component: str
    hostname: str
    customizations: frozenset[str]
    target_reference_concentration: float
    reference_id_sequence: tuple[str, ...]
    blank_id_sequence: tuple[str, ...]

    @property
    def all_identifiers(self) -> Iterator[str]:
        for value in self.reference_id_sequence:
            yield value
        for value in self.blank_id_sequence:
            yield value

    @staticmethod
    def _get_hostname_from_file(file: Path) -> str:
        matches = validate_file_name(file)
        return matches.group("hostname")

    @staticmethod
    def _get_id_from_file(file: Path) -> str:
        matches = validate_file_name(file)
        return matches.group("mnemonic_id")

    def validate_files(self, files: tuple[Path, ...]) -> None:
        existing_identifiers = tuple(self._get_id_from_file(file) for file in files)
        for identifier in tuple(self.all_identifiers):
            if identifier not in existing_identifiers:
                raise ValueError(f"File with identifier: {identifier} was not found")

    def check_file_belongs_to(self, file: Path) -> bool:
        identifier = self._get_id_from_file(file)
        hostname = self._get_hostname_from_file(file)
        return hostname == self.hostname and identifier in tuple(self.all_identifiers)

    def get_miscellaneous_from_file(self, file: Path) -> Miscellaneous:
        identifier = self._get_id_from_file(file)
        if identifier not in tuple(self.all_identifiers):
            raise ValueError(
                f"The id {identifier} was not found in the component QC template."
            )
        liquid: Liquid
        if identifier in self.reference_id_sequence:
            index = self.reference_id_sequence.index(identifier)
            liquid = SilicaBeadsInPbs(
                target_silica_beads_concentration=self.target_reference_concentration,
                silica_beads_diameter_um=1.0,
                # TODO: Don't just assume 1:9.
                pbs_formula="1:9",
            )
        else:
            index = self.blank_id_sequence.index(identifier)
            # TODO: Don't just assume 1:9.
            liquid = Pbs(pbs_formula="1:9")

        component_qc = ComponentQc(
            identifier=self.identifier,
            component=self.component,
            index=index,
            maintenance_procedure=self.maintenance_procedure,
        )
        return Miscellaneous(
            liquid=liquid,
            experiment=component_qc,
            operator=self.operator,
            customizations=self.customizations,
        )
