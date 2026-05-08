"""activity_track_fix_fk

Drop and recreate activity_track so it FKs event_record (1:1) instead of
event_record_detail. The previous migration linked it via event_record_detail's
shared PK, which conflicted with workout_details rows.

Revision ID: a4c1f1f10002
Revises: a4c1f1f10001

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4c1f1f10002"
down_revision: Union[str, None] = "a4c1f1f10001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS activity_track CASCADE;")
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["record_id"], ["event_record.id"], ondelete="CASCADE"),
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
