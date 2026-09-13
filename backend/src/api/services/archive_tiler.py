from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ArchiveTile:
    """
    A spatial tile extracted from an archive raster.

    x/y are pixel coordinates in the source raster.
    """

    tile_id: str
    x: int
    y: int
    width: int
    height: int
    image: Image.Image


def generate_tiles(
    image: Image.Image,
    tile_size: int = 224,
    stride: int = 168,
) -> list[ArchiveTile]:
    """
    Generate overlapping square tiles from an image.

    Default:
        tile size = 224 px
        stride    = 168 px

    This gives 56 px overlap between neighboring tiles.
    """

    if tile_size <= 0:
        raise ValueError("tile_size must be greater than 0.")

    if stride <= 0:
        raise ValueError("stride must be greater than 0.")

    width, height = image.size

    if width < tile_size or height < tile_size:
        raise ValueError(
            f"Image {width}x{height} is smaller than "
            f"tile size {tile_size}."
        )

    tiles: list[ArchiveTile] = []

    x_positions = _positions(
        length=width,
        tile_size=tile_size,
        stride=stride,
    )

    y_positions = _positions(
        length=height,
        tile_size=tile_size,
        stride=stride,
    )

    for y in y_positions:
        for x in x_positions:

            tile = image.crop(
                (
                    x,
                    y,
                    x + tile_size,
                    y + tile_size,
                )
            )

            tile_id = (
                f"x{x}_y{y}"
            )

            tiles.append(
                ArchiveTile(
                    tile_id=tile_id,
                    x=x,
                    y=y,
                    width=tile_size,
                    height=tile_size,
                    image=tile,
                )
            )

    return tiles


def _positions(
    length: int,
    tile_size: int,
    stride: int,
) -> list[int]:
    """
    Calculate tile start positions while guaranteeing that
    the final part of the raster is covered.
    """

    positions: list[int] = []

    position = 0

    while position + tile_size < length:
        positions.append(position)
        position += stride

    final_position = length - tile_size

    if not positions or positions[-1] != final_position:
        positions.append(final_position)

    return positions


def image_to_rgb_array(
    image: Image.Image,
) -> np.ndarray:
    """
    Convert a PIL image to a uint8 RGB numpy array.

    Useful for validation and future processing.
    """

    rgb = image.convert("RGB")

    return np.asarray(
        rgb,
        dtype=np.uint8,
    )


__all__ = [
    "ArchiveTile",
    "generate_tiles",
    "image_to_rgb_array",
]