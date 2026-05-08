"""activity_track

Revision ID: a4c1f1f10001
Revises: d15dee848b33

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4c1f1f10001"
down_revision: Union[str, None] = "d15dee848b33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_track",
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Numeric(10, 3), nullable=True),
        sa.Column("bbox_min_lat", sa.Numeric(10, 3), nullable=True),
        sa.Column("bbox_min_lon", sa.Numeric(10, 3), nullable=True),
        sa.Column("bbox_max_lat", sa.Numeric(10, 3), nullable=True),
        sa.Column("bbox_max_lon", sa.Numeric(10, 3), nullable=True),
        sa.Column("elevation_gain_meters", sa.Numeric(10, 3), nullable=True),
        sa.Column("elevation_loss_meters", sa.Numeric(10, 3), nullable=True),
        sa.Column("source_format", sa.String(10), nullable=True),
        sa.Column("track_points", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("streams", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["record_id"], ["event_record_detail.record_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("record_id"),
    )
    op.create_index(
        "ix_activity_track_bbox",
        "activity_track",
        ["bbox_min_lat", "bbox_min_lon", "bbox_max_lat", "bbox_max_lon"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_activity_track_bbox", table_name="activity_track")
    op.drop_table("activity_track")
