"""fix scene asset georeference type

Revision ID: 8ef9dad4bb35
Revises: 097a93a2efaa
Create Date: 2026-09-13 00:06:51.820663

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8ef9dad4bb35"
down_revision: Union[str, Sequence[str], None] = "097a93a2efaa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "sar_scene_assets",
        "has_georeference",
        existing_type=sa.VARCHAR(length=10),
        type_=sa.Boolean(),
        existing_nullable=True,
        postgresql_using="has_georeference::boolean",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "sar_scene_assets",
        "has_georeference",
        existing_type=sa.Boolean(),
        type_=sa.VARCHAR(length=10),
        existing_nullable=True,
    )
