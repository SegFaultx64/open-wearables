from typing import Annotated, Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.mappings import FKEventRecordDetail, numeric_10_3

from .event_record_detail import EventRecordDetail

_jsonb_any = Annotated[Any, mapped_column(JSONB)]
_str_10 = Annotated[str, mapped_column(String(10))]


class ActivityTrack(EventRecordDetail):
    """Per-activity GPS track + per-sample sensor streams parsed from FIT/GPX/TCX.

    Stored as JSONB:
      - track_points: list of {t (offset_seconds from start), lat, lon, ele}
      - streams:      dict of stream_name -> list of (t, value), e.g. heart_rate, power, cadence, speed, temperature
    Bounding box columns let routes filter spatially without loading the JSONB.
    """

    __tablename__ = "activity_track"
    __mapper_args__ = {"polymorphic_identity": "track"}

    record_id: Mapped[FKEventRecordDetail]

    sample_count: Mapped[int | None]
    distance_meters: Mapped[numeric_10_3 | None]

    bbox_min_lat: Mapped[numeric_10_3 | None]
    bbox_min_lon: Mapped[numeric_10_3 | None]
    bbox_max_lat: Mapped[numeric_10_3 | None]
    bbox_max_lon: Mapped[numeric_10_3 | None]

    elevation_gain_meters: Mapped[numeric_10_3 | None]
    elevation_loss_meters: Mapped[numeric_10_3 | None]

    source_format: Mapped[_str_10 | None]  # "fit" | "gpx" | "tcx"

    track_points: Mapped[_jsonb_any | None]
    streams: Mapped[_jsonb_any | None]
