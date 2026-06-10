"""Parsers for HEC-RAS project files (.prj, .pXX, .gXX, .uXX/.fXX/.qXX, .rasmap)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from .hdf_reader import read_geometry_associations
from .models import (
    FlowFile,
    Geometry,
    LayerAssociation,
    MapLayer,
    Plan,
    ProjectInventory,
    RasFile,
    Terrain,
)

PLAN_RE = re.compile(r"^\.p\d{2}$", re.IGNORECASE)
GEOM_RE = re.compile(r"^\.g\d{2}$", re.IGNORECASE)
UNSTEADY_RE = re.compile(r"^\.u\d{2}$", re.IGNORECASE)
STEADY_RE = re.compile(r"^\.f\d{2}$", re.IGNORECASE)
QUASI_RE = re.compile(r"^\.q\d{2}$", re.IGNORECASE)

# attribute-name fragments (lowercase) -> geometry association field
_RASMAP_ASSOC_FIELDS = {
    "terrain": "terrain",
    "landcover": "mannings",
    "land cover": "mannings",
    "nvalue": "mannings",
    "mannings": "mannings",
    "infiltration": "infiltration",
    "impervious": "impervious",
    "sediment": "sediment",
}


def read_text(path: Path) -> str:
    """Read a HEC-RAS text file, tolerating odd encodings."""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_keys(text: str) -> Dict[str, str]:
    """Parse ``Key=Value`` lines into a dict (first occurrence wins)."""
    keys: Dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in keys:
                keys[key] = value.strip()
    return keys


def parse_description(text: str) -> str:
    """Extract the BEGIN DESCRIPTION / END DESCRIPTION block, if present."""
    match = re.search(
        r"BEGIN DESCRIPTION:?\s*\n(.*?)END DESCRIPTION:?",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def is_hecras_project_file(path: Path) -> bool:
    """Distinguish a HEC-RAS .prj from a GIS projection .prj (WKT)."""
    try:
        head = read_text(path)[:2000]
    except OSError:
        return False
    return "Proj Title" in head or "Current Plan" in head


def find_project_file(folder: Path) -> Optional[Path]:
    candidates = sorted(folder.glob("*.prj"))
    for candidate in candidates:
        if is_hecras_project_file(candidate):
            return candidate
    return None


def parse_units(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ("English Units", "SI Units"):
            return stripped
    return ""


def parse_plan_file(path: Path) -> Plan:
    text = read_text(path)
    keys = parse_keys(text)
    title = keys.get("Plan Title", "")
    return Plan(
        file=RasFile(path=path, file_type="Plan", title=title),
        title=title,
        short_id=keys.get("Short Identifier", ""),
        geom_ext=keys.get("Geom File", ""),
        flow_ext=keys.get("Flow File", ""),
        simulation_date=keys.get("Simulation Date", ""),
        computation_interval=keys.get("Computation Interval", ""),
        output_interval=keys.get("Output Interval", ""),
        mapping_interval=keys.get("Mapping Interval", ""),
        program_version=keys.get("Program Version", ""),
        description=parse_description(text),
    )


def parse_geometry_file(path: Path) -> Geometry:
    keys = parse_keys(read_text(path))
    title = keys.get("Geom Title", "")
    return Geometry(
        file=RasFile(path=path, file_type="Geometry", title=title),
        title=title,
        program_version=keys.get("Program Version", ""),
    )


def parse_flow_file(path: Path, flow_type: str) -> FlowFile:
    keys = parse_keys(read_text(path))
    title = keys.get("Flow Title", "")
    return FlowFile(
        file=RasFile(path=path, file_type=f"{flow_type} Flow", title=title),
        flow_type=flow_type,
        title=title,
        program_version=keys.get("Program Version", ""),
    )


def _normalize_path_name(value: str) -> str:
    """'.\\Terrain\\T1.hdf' -> 't1.hdf' (basename, lowercase)."""
    return Path(value.replace("\\", "/")).name.lower()


def parse_rasmap(path: Path, inventory: ProjectInventory) -> Dict[str, Dict[str, LayerAssociation]]:
    """Pull terrain/map-layer/association info out of a .rasmap XML file.

    Returns geometry associations keyed by the geometry file reference
    (lower-cased basename, e.g. "muncie.g01.hdf").
    """
    associations: Dict[str, Dict[str, LayerAssociation]] = {}
    try:
        root = ET.fromstring(read_text(path))
    except ET.ParseError:
        return associations

    proj = root.find(".//RASProjectionFilename")
    if proj is not None:
        inventory.projection = proj.get("Filename", "")

    terrains_el = root.find(".//Terrains")
    if terrains_el is not None:
        for layer in terrains_el.iter("Layer"):
            inventory.terrains.append(
                Terrain(
                    name=layer.get("Name", ""),
                    filename=layer.get("Filename", ""),
                    priority=layer.get("Priority", ""),
                )
            )

    map_layers_el = root.find(".//MapLayers")
    if map_layers_el is not None:
        for layer in map_layers_el.iter("Layer"):
            inventory.map_layers.append(
                MapLayer(
                    name=layer.get("Name", ""),
                    layer_type=layer.get("Type", ""),
                    filename=layer.get("Filename", ""),
                )
            )

    # Geometry <-> layer associations. RAS Mapper has written these in a few
    # different shapes over the years, so match any element whose tag contains
    # "Association" and classify the attributes it carries.
    for element in root.iter():
        if "association" not in element.tag.lower() or not element.attrib:
            continue
        geometry_ref = (
            element.get("GeomFilename")
            or element.get("Filename")
            or element.get("Name", "")
        )
        if not geometry_ref:
            continue
        fields: Dict[str, LayerAssociation] = {}
        for attr_name, attr_value in element.attrib.items():
            lowered = attr_name.lower()
            for fragment, field_name in _RASMAP_ASSOC_FIELDS.items():
                if fragment in lowered:
                    assoc = fields.setdefault(field_name, LayerAssociation())
                    if "name" in lowered and "filename" not in lowered:
                        assoc.layer_name = attr_value
                    else:
                        assoc.filename = attr_value
                    break
        if fields:
            associations[_normalize_path_name(geometry_ref)] = fields
    return associations


def _resolve_layer_name(inventory: ProjectInventory, assoc: LayerAssociation) -> None:
    """Fill in a missing layer name by matching the filename against the
    terrain / map layer catalogs from the .rasmap file."""
    if assoc.layer_name or not assoc.filename:
        return
    target = _normalize_path_name(assoc.filename)
    for terrain in inventory.terrains:
        if _normalize_path_name(terrain.filename) == target:
            assoc.layer_name = terrain.name
            return
    for layer in inventory.map_layers:
        if _normalize_path_name(layer.filename) == target:
            assoc.layer_name = layer.name
            return


def _apply_geometry_associations(
    inventory: ProjectInventory,
    rasmap_assocs: Dict[str, Dict[str, LayerAssociation]],
) -> None:
    for geometry in inventory.geometries:
        # Best source: the compiled geometry HDF (.gXX.hdf), which stores the
        # associations HEC-RAS actually used.
        geom_hdf = geometry.file.path.with_name(geometry.file.path.name + ".hdf")
        fields = read_geometry_associations(geom_hdf)

        if fields is None:
            # Fall back to associations recorded in the .rasmap file.
            stem = geometry.file.path.name.lower()
            for geom_ref, assoc_fields in rasmap_assocs.items():
                if geom_ref.startswith(stem):
                    fields = assoc_fields
                    break

        if fields is None and len(inventory.terrains) == 1:
            fields = {
                "terrain": LayerAssociation(
                    layer_name=inventory.terrains[0].name,
                    filename=inventory.terrains[0].filename,
                )
            }

        if fields is None:
            continue
        for field_name, assoc in fields.items():
            _resolve_layer_name(inventory, assoc)
            setattr(geometry, field_name, assoc)


def scan_project(folder: Path) -> ProjectInventory:
    """Scan a HEC-RAS project folder and build the full inventory."""
    folder = folder.resolve()
    inventory = ProjectInventory(folder=folder)
    rasmap_assocs: Dict[str, Dict[str, LayerAssociation]] = {}

    prj_path = find_project_file(folder)
    if prj_path is not None:
        text = read_text(prj_path)
        keys = parse_keys(text)
        inventory.title = keys.get("Proj Title", "")
        inventory.current_plan = keys.get("Current Plan", "")
        inventory.units = parse_units(text)
        inventory.description = parse_description(text)
        inventory.project_file = RasFile(
            path=prj_path, file_type="Project", title=inventory.title
        )

    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix
        if PLAN_RE.match(suffix):
            inventory.plans.append(parse_plan_file(path))
        elif GEOM_RE.match(suffix):
            inventory.geometries.append(parse_geometry_file(path))
        elif UNSTEADY_RE.match(suffix):
            inventory.flows.append(parse_flow_file(path, "Unsteady"))
        elif STEADY_RE.match(suffix):
            inventory.flows.append(parse_flow_file(path, "Steady"))
        elif QUASI_RE.match(suffix):
            inventory.flows.append(parse_flow_file(path, "Quasi-Unsteady"))
        elif suffix.lower() == ".rasmap":
            inventory.other_files.append(
                RasFile(path=path, file_type="RAS Mapper", title="")
            )
            rasmap_assocs = parse_rasmap(path, inventory)
        elif suffix.lower() == ".hdf":
            inventory.other_files.append(
                RasFile(path=path, file_type="HDF Output", title="")
            )

    _apply_geometry_associations(inventory, rasmap_assocs)
    return inventory


def file_titles(inventory: ProjectInventory) -> Dict[str, str]:
    """Map extension (e.g. 'g01') -> title, for cross-referencing plans."""
    titles: Dict[str, str] = {}
    for geometry in inventory.geometries:
        titles[geometry.file.extension.lower()] = geometry.title
    for flow in inventory.flows:
        titles[flow.file.extension.lower()] = flow.title
    return titles
