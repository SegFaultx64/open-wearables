from typing import Annotated, Any
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import BaseDbModel
from app.mappings import numeric_10_3

_jsonb_any = Annotated[Any, mapped_column(JSONB)]


class ActivityTrack(BaseDbModel):
    """Per-activity GPS track + per-sample sensor streams parsed from FIT/GPX/TCX.

    1:1 with event_record (one track per workout). Stored separately from
    event_record_detail/workout_details since those are polymorphic on a shared
    record_id PK and can only hold one row per workout.

    JSONB columns:
      - track_points: list of {t, lat, lon, ele}
      - streams:      dict of stream_name -> [[t, value], ...]
    """

    __tablename__ = "activity_track"

    record_id: Mapped[UUID] = mapped_column(
        ForeignKey("event_record.id", ondelete="CASCADE"),
        primary_key=True,
    )

    sample_count: Mapped[int | None]
    distance_meters: Mapped[numeric_10_3 | None]

    bbox_min_lat: Mapped[numeric_10_3 | None]
    bbox_min_lon: Mapped[numeric_10_3 | None]
    bbox_max_lat: Mapped[numeric_10_3 | None]
    bbox_max_lon: Mapped[numeric_10_3 | None]

    elevation_gain_meters: Mapped[numeric_10_3 | None]
    elevation_loss_meters: Mapped[numeric_10_3 | None]

    source_format: Mapped[str | None] = mapped_column(String(10))

    track_points: Mapped[_jsonb_any | None]
    streams: Mapped[_jsonb_any | None]
