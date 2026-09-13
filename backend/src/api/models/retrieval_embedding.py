from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from src.api.db import Base


class RetrievalEmbedding(Base):
    __tablename__ = "retrieval_embeddings"

    id = Column(BigInteger, primary_key=True, index=True)

    asset_id = Column(
        BigInteger,
        ForeignKey("sar_assets.id", ondelete="CASCADE"),
        nullable=False,
    )

    model_name = Column(String(100), nullable=False)
    model_version = Column(String(100), nullable=False)

    dimension = Column(Integer, nullable=False)

    embedding_index = Column(Integer, nullable=True)

    index_name = Column(String(255), nullable=True)

    processing_version = Column(String(100), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
