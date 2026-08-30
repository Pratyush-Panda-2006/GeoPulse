from sqlalchemy import BigInteger, Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.sql import func

from src.api.db import Base

JsonType = JSONB().with_variant(JSON(), "sqlite")

class Detection(Base):
    __tablename__ = "detections"

    id = Column(BigInteger, primary_key=True, index=True)

    job_id = Column(
        BigInteger,
        ForeignKey("change_detection_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    geometry = Column(JsonType, nullable=False)
    properties = Column(JsonType, nullable=False)

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
