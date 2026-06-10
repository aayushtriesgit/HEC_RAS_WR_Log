"""Write a HEC-RAS project inventory to a Water Simulation Log style workbook.

The default workbook has three sheets (Plans, Geometries, Flow Files).
"Notes" and "Description" columns are intentionally left empty for the
engineer to fill in.

NOTE: The exact sheet names / column order can be adjusted in build_rows()
below to match the official log template.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .models import ProjectInventory
from .parsers import file_titles

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="44546A")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)

PLANS_HEADERS = [
    "Plan Name",
    "Plan Extension",
    "Short ID",
    "Geometry Extension",
    "Geometry Name",
    "Flow Extension",
    "Flow Name",
    "Simulation Date",
    "Computation Interval",
    "Output Interval",
    "Mapping Interval",
    "Notes",
    "Description",
]
GEOM_HEADERS = [
    "Geometry Name",
    "Geometry Extension",
    "Terrain",
    "Manning's n (Land Cover)",
    "Infiltration",
    "% Impervious",
    "Sediment Bed Material",
    "Notes",
    "Description",
]
FLOW_HEADERS = [
    "Flow Name",
    "Flow Extension",
    "Flow Type",
    "Program Version",
    "Notes",
    "Description",
]

SheetData = Tuple[List[str], List[Sequence[object]]]


def _write_table(sheet: Worksheet, headers: Sequence[str], rows: List[Sequence[object]]) -> None:
    sheet.append(list(headers))
    for cell in sheet[sheet.max_row]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN
    for row in rows:
        sheet.append(list(row))
    for col_idx, header in enumerate(headers, start=1):
        width = max(
            [len(str(header))]
            + [len(str(row[col_idx - 1] or "")) for row in rows]
        )
        sheet.column_dimensions[get_column_letter(col_idx)].width = min(width + 3, 60)
    sheet.freeze_panes = "A2"


def build_rows(inventory: ProjectInventory) -> Dict[str, SheetData]:
    """Build the row data for every sheet, keyed by sheet name."""
    titles = file_titles(inventory)

    plan_rows: List[Sequence[object]] = []
    for plan in inventory.plans:
        plan_rows.append(
            (
                plan.title,
                plan.file.extension,
                plan.short_id,
                plan.geom_ext,
                titles.get(plan.geom_ext.lower(), ""),
                plan.flow_ext,
                titles.get(plan.flow_ext.lower(), ""),
                plan.simulation_date,
                plan.computation_interval,
                plan.output_interval,
                plan.mapping_interval,
                "",  # Notes - left empty on purpose
                "",  # Description - left empty on purpose
            )
        )

    geom_rows: List[Sequence[object]] = []
    for geometry in inventory.geometries:
        geom_rows.append(
            (
                geometry.title,
                geometry.file.extension,
                geometry.terrain.display,
                geometry.mannings.display,
                geometry.infiltration.display,
                geometry.impervious.display,
                geometry.sediment.display,
                "",  # Notes
                "",  # Description
            )
        )

    flow_rows: List[Sequence[object]] = []
    for flow in inventory.flows:
        flow_rows.append(
            (
                flow.title,
                flow.file.extension,
                flow.flow_type,
                flow.program_version,
                "",  # Notes
                "",  # Description
            )
        )

    return {
        "Plans": (PLANS_HEADERS, plan_rows),
        "Geometries": (GEOM_HEADERS, geom_rows),
        "Flow Files": (FLOW_HEADERS, flow_rows),
    }


def write_inventory(
    inventory: ProjectInventory,
    output: Path,
    template: Optional[Path] = None,
) -> Path:
    """Write the inventory to ``output``.

    If ``template`` is given, the workbook is loaded from it and data rows are
    appended to any sheet whose name matches an inventory section (Plans,
    Geometries, Flow Files); headers are assumed to already exist in the
    template. Missing sheets are created with default headers.
    """
    sections = build_rows(inventory)

    if template is not None:
        workbook = load_workbook(template)
        for sheet_name, (headers, rows) in sections.items():
            if sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                for row in rows:
                    sheet.append(list(row))
            else:
                sheet = workbook.create_sheet(sheet_name)
                _write_table(sheet, headers, rows)
    else:
        workbook = Workbook()
        workbook.remove(workbook.active)
        for sheet_name, (headers, rows) in sections.items():
            sheet = workbook.create_sheet(sheet_name)
            _write_table(sheet, headers, rows)

    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)
    return output
