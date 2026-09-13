from __future__ import annotations

from dataclasses import dataclass

from rasterio.transform import Affine
from rasterio.warp import transform_bounds


@dataclass(frozen=True)
class GeographicTileBounds:
    """
    Geographic footprint of a raster tile.

    The returned bounds are always expressed in EPSG:4326.
    """

    west: float
    south: float
    east: float
    north: float
    crs: str


def tile_bounds(
    transform: Affine,
    source_crs,
    x: int,
    y: int,
    width: int,
    height: int,
) -> GeographicTileBounds:
    """
    Convert a tile's pixel coordinates into geographic bounds.

    Parameters
    ----------
    transform:
        Rasterio affine transform for the source raster.

    source_crs:
        CRS of the source raster.

    x, y:
        Pixel coordinates of the tile's upper-left corner.

    width, height:
        Tile dimensions in pixels.

    Returns
    -------
    GeographicTileBounds
        Tile bounds in EPSG:4326.
    """

    if width <= 0 or height <= 0:
        raise ValueError(
            "Tile width and height must be greater than zero."
        )

    if source_crs is None:
        raise ValueError(
            "Source raster CRS is required."
        )

    # Pixel edges, not pixel centers.
    left, top = transform * (x, y)

    right, bottom = transform * (
        x + width,
        y + height,
    )

    min_x = min(left, right)
    max_x = max(left, right)
    min_y = min(bottom, top)
    max_y = max(bottom, top)

    west, south, east, north = transform_bounds(
        source_crs,
        "EPSG:4326",
        min_x,
        min_y,
        max_x,
        max_y,
        densify_pts=21,
    )

    return GeographicTileBounds(
        west=float(west),
        south=float(south),
        east=float(east),
        north=float(north),
        crs="EPSG:4326",
    )


__all__ = [
    "GeographicTileBounds",
    "tile_bounds",
]