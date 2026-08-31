from sqlalchemy import BigInteger, Column, Date, DateTime, Integer, Float, String, Text
from sqlalchemy.sql import func

from src.api.db import Base


class SARRequest(Base):
    __tablename__ = "sar_requests"

    id = Column(BigInteger, primary_key=True, index=True)

    bbox_min_lon = Column(Float, nullable=False)
    bbox_min_lat = Column(Float, nullable=False)
    bbox_max_lon = Column(Float, nullable=False)
    bbox_max_lat = Column(Float, nullable=False)

    t1_date_from = Column(Date, nullable=False)
    t1_date_to = Column(Date, nullable=False)
    t2_date_from = Column(Date, nullable=False)
    t2_date_to = Column(Date, nullable=False)

    resolution_width = Column(Integer, nullable=False)
    resolution_height = Column(Integer, nullable=False)

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