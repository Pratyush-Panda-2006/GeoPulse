import datetime
from sqlalchemy import Column, String, Float, Text, DateTime
from src.api.db import Base

class NemotronCache(Base):
    __tablename__ = "nemotron_cache"
    
    cache_key = Column(String, primary_key=True, index=True)
    category = Column(String, nullable=True)
    visual_confidence = Column(Float, nullable=True)
    short_summary = Column(Text, nullable=True)
    visual_cues = Column(Text, nullable=True)
    uncertainty = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
