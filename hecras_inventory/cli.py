"""Command line interface for the HEC-RAS project inventory tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .excel_writer import write_inventory
from .parsers import scan_project


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="hecras-inventory",
        description=(
            "Scan a HEC-RAS project folder (.prj, .pXX, .gXX, .uXX/.fXX/.qXX, "
            ".rasmap) and write the project inventory to an Excel spreadsheet."
        ),
    )
    parser.add_argument("project_folder", type=Path, help="HEC-RAS project folder")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .xlsx path (default: <project folder>/<folder name>_inventory.xlsx)",
    )
    parser.add_argument(
        "-t",
        "--template",
        type=Path,
        default=None,
        help="Optional .xlsx template to populate instead of creating a new workbook",
    )
    args = parser.parse_args(argv)

    folder = args.project_folder
    if not folder.is_dir():
        parser.error(f"not a directory: {folder}")
    if args.template is not None and not args.template.is_file():
        parser.error(f"template not found: {args.template}")

    inventory = scan_project(folder)
    if inventory.project_file is None:
        print(
            f"warning: no HEC-RAS .prj file found in {folder}; "
            "writing inventory from the other files found.",
            file=sys.stderr,
        )

    output = args.output or folder / f"{folder.resolve().name}_inventory.xlsx"
    write_inventory(inventory, output, template=args.template)

    print(f"Project:    {inventory.title or '(no title)'}")
    print(
        f"Found:      {len(inventory.plans)} plan(s), "
        f"{len(inventory.geometries)} geometry file(s), "
        f"{len(inventory.flows)} flow file(s), "
        f"{len(inventory.terrains)} terrain(s)"
    )
    print(f"Wrote:      {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
