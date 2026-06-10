# HEC-RAS Water Simulation Log Generator

A Python tool that scans a HEC-RAS project folder and automatically populates a
Water Simulation Log Excel workbook with plan, geometry, flow and terrain
information — so you don't have to fill the log sheet in by hand after every
ODA analysis.

It reads:

- **`.prj`** — project title, unit system, current plan (GIS projection `.prj`
  files are detected and skipped)
- **`.pXX`** plan files — plan title, short ID, associated geometry / flow file
  extensions, simulation date, computation / output / mapping intervals
- **`.gXX`** geometry files — geometry title
- **`.gXX.hdf`** compiled geometry files — the terrain, Manning's n (land
  cover), infiltration, % impervious and sediment bed material layers that
  HEC-RAS actually associated with each geometry
- **`.uXX` / `.fXX` / `.qXX`** flow files — flow title and type
  (unsteady / steady / quasi-unsteady)
- **`.rasmap`** — terrain layers, land classification layers, and
  geometry–layer associations (used as a fallback when no `.gXX.hdf` exists)

## Installation

Requires Python 3.9+.

```bash
pip install -r requirements.txt
```

## Usage

Just run it and answer the two questions:

```bash
python -m hecras_inventory
```

```text
Enter the HEC-RAS project folder path: C:\Projects\Muncie
Enter the folder to save the Excel log file: C:\Projects\Muncie\Logs
```

Or pass the folders directly:

```bash
python -m hecras_inventory <project_folder> -s <save_folder> [-t template.xlsx]
```

The output file is named `<Project Title>_Simulation_Log.xlsx`.

## Output

The workbook contains three sheets. The **Notes** and **Description** columns
are intentionally left empty for the engineer to fill in.

| Sheet      | Columns                                                                                                                       |
|------------|-------------------------------------------------------------------------------------------------------------------------------|
| Plans      | Plan name, plan extension, short ID, geometry extension + name, flow extension + name, simulation date, intervals, notes, description |
| Geometries | Geometry name, extension, terrain, Manning's n (land cover), infiltration, % impervious, sediment bed material, notes, description |
| Flow Files | Flow name, extension, flow type, program version, notes, description                                                           |

## Using your own log template

Pass `-t / --template` with your own `.xlsx` log sheet. Data rows are appended
to any sheet named `Plans`, `Geometries` or `Flow Files` (your headers are kept
as-is); any missing sheets are created with default headers.

If your template uses different sheet names or column order, adjust
`build_rows()` in `hecras_inventory/excel_writer.py` — all parsed data is
available on the `ProjectInventory` model in `hecras_inventory/models.py`.

## How geometry–layer associations are found

1. **Preferred:** read the `/Geometry` attributes inside the compiled geometry
   HDF (`.gXX.hdf`) — `Terrain Filename/Layername`, `Land Cover
   Filename/Layername`, `Infiltration Filename/Layername`, `Percent Impervious
   Filename/Layername`, `Sediment Bed Material Filename/Layername`. This is
   what HEC-RAS actually used in the last geometry preprocessing run.
2. **Fallback:** association entries in the `.rasmap` file.
3. Layer filenames are cross-referenced against the `.rasmap` terrain and land
   classification catalogs to recover display names.

A small synthetic example project is included in `sample_project/` for testing
(`Muncie.g01.hdf` is a generated fixture containing only the association
attributes).
