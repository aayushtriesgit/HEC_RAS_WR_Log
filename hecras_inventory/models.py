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
    mapping_interval: str = ""
    program_version: str = ""
    description: str = ""


@dataclass
class LayerAssociation:
    """One layer associated with a geometry (terrain, Manning's n, ...)."""

    layer_name: str = ""      # display name of the layer (e.g. "TerrainWithChannel")
    filename: str = ""        # path of the layer's HDF/raster file

    @property
    def display(self) -> str:
        """Best available label for spreadsheet output."""
        if self.layer_name:
            return self.layer_name
        if self.filename:
            stem = Path(self.filename.replace("\\", "/")).name
            return stem[:-4] if stem.lower().endswith(".hdf") else stem
        return ""


@dataclass
class Geometry:
    file: RasFile
    title: str = ""
    program_version: str = ""
    terrain: LayerAssociation = field(default_factory=LayerAssociation)
    mannings: LayerAssociation = field(default_factory=LayerAssociation)
    infiltration: LayerAssociation = field(default_factory=LayerAssociation)
    impervious: LayerAssociation = field(default_factory=LayerAssociation)
    sediment: LayerAssociation = field(default_factory=LayerAssociation)


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
class MapLayer:
    """A map / land classification layer listed in the .rasmap file."""

    name: str = ""
    layer_type: str = ""      # e.g. "LandCoverLayer", "MapLayer"
    filename: str = ""


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
    map_layers: List[MapLayer] = field(default_factory=list)
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
