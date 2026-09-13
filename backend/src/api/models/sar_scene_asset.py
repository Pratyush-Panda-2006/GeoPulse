from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from src.api.db import Base


class SARSceneAsset(Base):
    """
    AOI-specific raster asset downloaded from a canonical Sentinel-1 scene.

    A single Sentinel scene may have multiple AOI-specific assets, so these
    records are intentionally separate from SARScene itself.
    """

    __tablename__ = "sar_scene_assets"

    id = Column(BigInteger, primary_key=True, index=True)

    scene_id = Column(
        BigInteger,
        ForeignKey("sar_scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    bbox_min_lon = Column(Float, nullable=False)
    bbox_min_lat = Column(Float, nullable=False)
    bbox_max_lon = Column(Float, nullable=False)
    bbox_max_lat = Column(Float, nullable=False)

    storage_key = Column(Text, nullable=False)

    mime_type = Column(String(100), nullable=False, default="image/tiff")

    file_size_bytes = Column(BigInteger)
    checksum_sha256 = Column(String(64))

    width = Column(Integer)
    height = Column(Integer)
    band_count = Column(Integer)
    bands = Column(String(100))

    crs = Column(String(100))
    has_georeference = Column(
        Boolean,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "scene_id",
            "bbox_min_lon",
            "bbox_min_lat",
            "bbox_max_lon",
            "bbox_max_lat",
            name="uq_sar_scene_asset_scene_bbox",
        ),
    )
