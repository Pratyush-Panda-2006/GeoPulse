"""add sar scene assets

Revision ID: 097a93a2efaa
Revises: add_retrieval_embeddings
Create Date: 2026-09-12 23:55:45.122467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '097a93a2efaa'
down_revision: Union[str, Sequence[str], None] = 'add_retrieval_embeddings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sar_scene_assets",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("scene_id", sa.BigInteger(), nullable=False),
        sa.Column("bbox_min_lon", sa.Float(), nullable=False),
        sa.Column("bbox_min_lat", sa.Float(), nullable=False),
        sa.Column("bbox_max_lon", sa.Float(), nullable=False),
        sa.Column("bbox_max_lat", sa.Float(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column(
            "mime_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("band_count", sa.Integer(), nullable=True),
        sa.Column("bands", sa.String(length=100), nullable=True),
        sa.Column("crs", sa.String(length=100), nullable=True),
        sa.Column("has_georeference", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"],
            ["sar_scenes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scene_id",
            "bbox_min_lon",
            "bbox_min_lat",
            "bbox_max_lon",
            "bbox_max_lat",
            name="uq_sar_scene_asset_scene_bbox",
        ),
    )

    op.create_index(
        op.f("ix_sar_scene_assets_id"),
        "sar_scene_assets",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_sar_scene_assets_scene_id"),
        "sar_scene_assets",
        ["scene_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_sar_scene_assets_scene_id"),
        table_name="sar_scene_assets",
    )

    op.drop_index(
        op.f("ix_sar_scene_assets_id"),
        table_name="sar_scene_assets",
    )

    op.drop_table("sar_scene_assets")
