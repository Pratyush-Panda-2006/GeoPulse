"""add retrieval embeddings

Revision ID: add_retrieval_embeddings
Revises: c9a124acdc43
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_retrieval_embeddings"
down_revision: Union[str, Sequence[str], None] = "c9a124acdc43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "retrieval_embeddings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("embedding_index", sa.Integer(), nullable=True),
        sa.Column("index_name", sa.String(length=255), nullable=True),
        sa.Column("processing_version", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["sar_assets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_retrieval_embeddings_id",
        "retrieval_embeddings",
        ["id"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_retrieval_embedding_asset_model_version",
        "retrieval_embeddings",
        ["asset_id", "model_name", "model_version", "processing_version"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_retrieval_embedding_asset_model_version",
        "retrieval_embeddings",
        type_="unique",
    )
    op.drop_index(
        "ix_retrieval_embeddings_id",
        table_name="retrieval_embeddings",
    )
    op.drop_table("retrieval_embeddings")
