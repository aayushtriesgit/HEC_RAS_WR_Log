"""Data model for a HEC-RAS project inventory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class RasFile:
    """A single file that belongs to the HEC-RAS project."""

    path: Path
    file_type: str            # e.g. "Plan", "Geometry", "Unsteady Flow", ...
    title: str = ""           # title read from inside the file, if any

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def extension(self) -> str:
        return self.path.suffix.lstrip(".")


@dataclass
class Plan:
    file: RasFile
    title: str = ""
    short_id: str = ""
    geom_ext: str = ""        # e.g. "g01" (extension of the associated geometry)
    flow_ext: str = ""        # e.g. "u01" / "f01"
    simulation_date: str = ""
    computation_interval: str = ""
    output_interval: str = ""
    program_version: str = ""


@dataclass
class Geometry:
    file: RasFile
    title: str = ""
    program_version: str = ""
    terrain_name: str = ""    # terrain associated through the .rasmap file


@dataclass
class FlowFile:
    file: RasFile
    flow_type: str = ""       # "Steady", "Unsteady" or "Quasi-Unsteady"
    title: str = ""
    program_version: str = ""


@dataclass
class Terrain:
    name: str = ""
    filename: str = ""        # path as written in the .rasmap file
    priority: str = ""


@dataclass
class TerrainAssociation:
    geometry: str = ""        # geometry file or layer name
    terrain: str = ""         # terrain name


@dataclass
class ProjectInventory:
    folder: Path
    project_file: Optional[RasFile] = None
    title: str = ""
    units: str = ""
    current_plan: str = ""
    description: str = ""
    projection: str = ""      # projection filename from the .rasmap file

    plans: List[Plan] = field(default_factory=list)
    geometries: List[Geometry] = field(default_factory=list)
    flows: List[FlowFile] = field(default_factory=list)
    terrains: List[Terrain] = field(default_factory=list)
    terrain_associations: List[TerrainAssociation] = field(default_factory=list)
    other_files: List[RasFile] = field(default_factory=list)

    def all_files(self) -> List[RasFile]:
        files: List[RasFile] = []
        if self.project_file:
            files.append(self.project_file)
        files.extend(p.file for p in self.plans)
        files.extend(g.file for g in self.geometries)
        files.extend(f.file for f in self.flows)
        files.extend(self.other_files)
        return files
