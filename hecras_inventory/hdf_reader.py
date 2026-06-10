"""Read geometry layer associations from compiled geometry HDF files (.gXX.hdf).

HEC-RAS 6.x records which terrain, Manning's n (land cover), infiltration,
percent impervious and sediment bed material layers are associated with a
geometry as attributes of the ``/Geometry`` group in the compiled geometry
HDF file, e.g.::

    Terrain Filename              .\\Terrain\\Terrain.hdf
    Terrain Layername             Terrain
    Land Cover Filename           .\\LandCover.hdf
    Land Cover Layername          LandCover
    Infiltration Filename         .\\Infiltration.hdf
    Infiltration Layername        Infiltration
    Sediment Bed Material Filename ...

Reading these requires the optional ``h5py`` package. If it is not installed
(or the .hdf file does not exist) the tool falls back to the .rasmap file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from .models import LayerAssociation

try:
    import h5py
except ImportError:  # pragma: no cover - optional dependency
    h5py = None

# spreadsheet field -> attribute prefix inside /Geometry
_ASSOCIATION_PREFIXES = {
    "terrain": "Terrain",
    "mannings": "Land Cover",
    "infiltration": "Infiltration",
    "impervious": "Percent Impervious",
    "sediment": "Sediment Bed Material",
}


def _decode(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()


def read_geometry_associations(geom_hdf: Path) -> Optional[Dict[str, LayerAssociation]]:
    """Return {field: LayerAssociation} from a .gXX.hdf file, or None."""
    if h5py is None or not geom_hdf.is_file():
        return None
    try:
        with h5py.File(geom_hdf, "r") as hdf:
            if "Geometry" not in hdf:
                return None
            attrs = {key: _decode(val) for key, val in hdf["Geometry"].attrs.items()}
    except OSError:
        return None

    associations: Dict[str, LayerAssociation] = {}
    for field_name, prefix in _ASSOCIATION_PREFIXES.items():
        filename = attrs.get(f"{prefix} Filename", "")
        layer_name = attrs.get(f"{prefix} Layername", "")
        if filename or layer_name:
            associations[field_name] = LayerAssociation(
                layer_name=layer_name, filename=filename
            )
    return associations or None
