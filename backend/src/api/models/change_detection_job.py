from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.sql import func

from src.api.db import Base

# Fallback to JSON if PostgreSQL JSONB isn't available
# Neon uses Postgres so JSONB is supported natively.
JsonType = JSONB().with_variant(JSON(), "sqlite")

class ChangeDetectionJob(Base):
    __tablename__ = "change_detection_jobs"

    id = Column(BigInteger, primary_key=True, index=True)

    scene_before_id = Column(
        BigInteger,
        ForeignKey("sar_scenes.id", ondelete="CASCADE"),
        nullable=False,
    )

    scene_after_id = Column(
        BigInteger,
        ForeignKey("sar_scenes.id", ondelete="CASCADE"),
        nullable=False,
    )

    model_version = Column(String(50))
    status = Column(String(30), nullable=False, default="created")
    
    change_percentage = Column(Float)
    confidence = Column(Float)
    
    result_asset_id = Column(
        BigInteger,
        ForeignKey("sar_assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    metrics = Column(JsonType)

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
