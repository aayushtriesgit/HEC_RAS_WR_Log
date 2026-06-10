"""Parsers for HEC-RAS project files (.prj, .pXX, .gXX, .uXX/.fXX/.qXX, .rasmap)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from .models import (
    FlowFile,
    Geometry,
    Plan,
    ProjectInventory,
    RasFile,
    Terrain,
    TerrainAssociation,
)

PLAN_RE = re.compile(r"^\.p\d{2}$", re.IGNORECASE)
GEOM_RE = re.compile(r"^\.g\d{2}$", re.IGNORECASE)
UNSTEADY_RE = re.compile(r"^\.u\d{2}$", re.IGNORECASE)
STEADY_RE = re.compile(r"^\.f\d{2}$", re.IGNORECASE)
QUASI_RE = re.compile(r"^\.q\d{2}$", re.IGNORECASE)


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
        program_version=keys.get("Program Version", ""),
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


def parse_rasmap(path: Path, inventory: ProjectInventory) -> None:
    """Pull terrain, projection and association info out of a .rasmap XML file."""
    try:
        root = ET.fromstring(read_text(path))
    except ET.ParseError:
        return

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

    # Geometry <-> terrain associations. RAS Mapper has written these in a few
    # different shapes over the years, so match any element whose tag contains
    # "Association" and read the attributes it carries.
    for element in root.iter():
        if "association" not in element.tag.lower() or len(element.attrib) == 0:
            continue
        geometry = (
            element.get("GeomFilename")
            or element.get("Filename")
            or element.get("Name", "")
        )
        terrain = element.get("TerrainFilename") or element.get("TerrainName", "")
        if geometry or terrain:
            inventory.terrain_associations.append(
                TerrainAssociation(geometry=geometry, terrain=terrain)
            )


def _terrain_for_geometry(inventory: ProjectInventory, geom_path: Path) -> str:
    """Find the terrain associated with a geometry via the .rasmap data."""
    stem = geom_path.name.lower()  # e.g. "project.g01"
    for assoc in inventory.terrain_associations:
        geom_ref = Path(assoc.geometry.replace("\\", "/")).name.lower()
        if geom_ref.startswith(stem):
            terrain_ref = Path(assoc.terrain.replace("\\", "/")).name
            return re.sub(r"\.hdf$", "", terrain_ref, flags=re.IGNORECASE)
    if len(inventory.terrains) == 1:
        return inventory.terrains[0].name
    return ""


def scan_project(folder: Path) -> ProjectInventory:
    """Scan a HEC-RAS project folder and build the full inventory."""
    folder = folder.resolve()
    inventory = ProjectInventory(folder=folder)

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
            parse_rasmap(path, inventory)
        elif suffix.lower() == ".hdf":
            inventory.other_files.append(
                RasFile(path=path, file_type="HDF Output", title="")
            )

    for geometry in inventory.geometries:
        geometry.terrain_name = _terrain_for_geometry(inventory, geometry.file.path)

    return inventory


def file_titles(inventory: ProjectInventory) -> Dict[str, str]:
    """Map extension (e.g. 'g01') -> title, for cross-referencing plans."""
    titles: Dict[str, str] = {}
    for geometry in inventory.geometries:
        titles[geometry.file.extension.lower()] = geometry.title
    for flow in inventory.flows:
        titles[flow.file.extension.lower()] = flow.title
    return titles
