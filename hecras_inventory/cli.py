"""Command line interface for the HEC-RAS Water Simulation Log tool.

Run with no arguments and the program will ask for:
  1. the HEC-RAS project folder, and
  2. the folder where the generated Excel file should be saved.

Both can also be given directly on the command line.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .excel_writer import write_inventory
from .parsers import scan_project


def _ask_for_folder(prompt: str, must_exist: bool = True) -> Path:
    """Keep asking until the user enters a usable folder path."""
    while True:
        raw = input(prompt).strip().strip('"').strip("'")
        if not raw:
            print("  Please enter a folder path.")
            continue
        folder = Path(raw).expanduser()
        if must_exist and not folder.is_dir():
            print(f"  Folder not found: {folder}  -- please try again.")
            continue
        return folder


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="hecras-inventory",
        description=(
            "Scan a HEC-RAS project folder (.prj, .pXX, .gXX, .uXX/.fXX/.qXX, "
            ".rasmap, .gXX.hdf) and write a Water Simulation Log Excel file."
        ),
    )
    parser.add_argument(
        "project_folder",
        type=Path,
        nargs="?",
        default=None,
        help="HEC-RAS project folder (you will be asked if omitted)",
    )
    parser.add_argument(
        "-s",
        "--save-folder",
        type=Path,
        default=None,
        help="Folder to save the generated Excel file (you will be asked if omitted)",
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
    if folder is None:
        folder = _ask_for_folder("Enter the HEC-RAS project folder path: ")
    elif not folder.is_dir():
        parser.error(f"not a directory: {folder}")

    save_folder = args.save_folder
    if save_folder is None:
        save_folder = _ask_for_folder(
            "Enter the folder to save the Excel log file: ", must_exist=False
        )

    if args.template is not None and not args.template.is_file():
        parser.error(f"template not found: {args.template}")

    inventory = scan_project(folder)
    if inventory.project_file is None:
        print(
            f"warning: no HEC-RAS .prj file found in {folder}; "
            "writing inventory from the other files found.",
            file=sys.stderr,
        )

    base_name = inventory.title or folder.resolve().name
    safe_name = re.sub(r'[\\/:*?"<>|]+', "_", base_name).strip() or "HECRAS_Project"
    output = save_folder / f"{safe_name}_Simulation_Log.xlsx"

    write_inventory(inventory, output, template=args.template)

    print()
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
