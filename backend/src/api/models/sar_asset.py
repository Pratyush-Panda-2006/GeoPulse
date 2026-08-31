from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from src.api.db import Base


class SARAsset(Base):
    __tablename__ = "sar_assets"

    id = Column(BigInteger, primary_key=True, index=True)

    request_id = Column(
        BigInteger,
        ForeignKey("sar_requests.id", ondelete="CASCADE"),
        nullable=False,
    )

    scene_id = Column(
        BigInteger,
        ForeignKey("sar_scenes.id", ondelete="CASCADE"),
        nullable=True,
    )

    asset_key = Column(String(255), nullable=True)

    time_label = Column(String(2), nullable=False)

    storage_key = Column(Text, nullable=False)

    mime_type = Column(String(100))
    file_size_bytes = Column(BigInteger)
    checksum_sha256 = Column(String(64))

    width = Column(Integer)
    height = Column(Integer)
    band_count = Column(Integer)
    bands = Column(String(100))

    crs = Column(String(100))

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "time_label IN ('T1', 'T2')",
            name="chk_sar_asset_time_label",
        ),
        UniqueConstraint(
            "request_id", "time_label", name="uq_sar_asset_request_time"
        ),
        UniqueConstraint(
            "scene_id", "asset_key", name="uq_sar_asset_scene_key"
        ),
    )