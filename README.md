# HEC-RAS Project Inventory

A Python tool that scans a HEC-RAS project folder, reads the project (`.prj`),
plan (`.pXX`), geometry (`.gXX`), flow (`.uXX` / `.fXX` / `.qXX`) and RAS Mapper
(`.rasmap`) files, and writes the project inventory — file names, extensions,
titles, plan/geometry/flow associations, terrain info, etc. — to an Excel
spreadsheet.

## Installation

Requires Python 3.9+.

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m hecras_inventory <path/to/hecras/project/folder> [-o output.xlsx] [-t template.xlsx]
```

Examples:

```bash
# Create <folder name>_inventory.xlsx inside the project folder
python -m hecras_inventory sample_project

# Write to a specific output file
python -m hecras_inventory sample_project -o muncie_inventory.xlsx

# Populate a copy of your own spreadsheet template
python -m hecras_inventory sample_project -t my_template.xlsx -o filled.xlsx
```

## Output

By default the workbook contains five sheets:

| Sheet      | Contents                                                                                         |
|------------|--------------------------------------------------------------------------------------------------|
| Project    | Project title, units, current plan, description, projection, file counts                          |
| Files      | Every project file: name, extension, file type, title, full path                                  |
| Plans      | Each plan with its short ID, associated geometry/flow files (and their titles), simulation dates  |
| Geometries | Each geometry with its title and the terrain associated through the `.rasmap` file                |
| Terrains   | Terrain layers defined in the `.rasmap` file (name, HDF filename, priority)                       |

## Using your own spreadsheet template

Pass `-t / --template` with an `.xlsx` file. Data rows are appended to any sheet
named `Project`, `Files`, `Plans`, `Geometries` or `Terrains` (headers in the
template are kept as-is); any missing sheets are created with default headers.

If your template uses a different layout (different sheet names, column order,
or a single combined sheet), adjust `build_rows()` in
`hecras_inventory/excel_writer.py` — all parsed data is available on the
`ProjectInventory` model in `hecras_inventory/models.py`.

## What gets parsed

- **`.prj` (project file):** project title, unit system, current plan,
  description block. GIS projection `.prj` files (WKT) are detected and skipped.
- **`.pXX` (plan files):** plan title, short identifier, associated geometry and
  flow file extensions, simulation date, computation/output intervals, program
  version.
- **`.gXX` (geometry files):** geometry title and program version.
- **`.uXX` / `.fXX` / `.qXX` (flow files):** flow title, flow type
  (unsteady / steady / quasi-unsteady), program version.
- **`.rasmap` (RAS Mapper):** terrain layers, geometry–terrain associations,
  and the spatial projection filename.
- **`.hdf` files** are listed in the file inventory as HDF outputs.

A small synthetic example project is included in `sample_project/` for testing.
