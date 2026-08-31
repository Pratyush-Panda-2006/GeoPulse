from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from src.api.db import Base


class SARScene(Base):
    __tablename__ = "sar_scenes"

    id = Column(BigInteger, primary_key=True, index=True)

    provider = Column(String(50), nullable=False)
    scene_id = Column(String(255), nullable=False)

    acquisition_date = Column(DateTime(timezone=True), nullable=False)

    bbox_min_lon = Column(Float)
    bbox_min_lat = Column(Float)
    bbox_max_lon = Column(Float)
    bbox_max_lat = Column(Float)

    crs = Column(String(100))
    has_georeference = Column(Boolean, nullable=True, default=False)

    r2_object_key = Column(Text)
    file_size_bytes = Column(BigInteger)
    checksum_sha256 = Column(String(64))

    status = Column(String(30), nullable=False, default="created")
    error_message = Column(Text)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "provider", "scene_id", name="uq_sar_scene_provider_scene_id"
        ),
    )