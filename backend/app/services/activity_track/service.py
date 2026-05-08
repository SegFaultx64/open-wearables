"""Service layer for activity tracks: ingest a FIT/GPX byte payload, persist as
ActivityTrack rows linked to the matching event_record."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from app.database import DbSession
from app.models import ActivityTrack, DataSource, EventRecord

from .parser import ParsedTrack, parse_fit, parse_gpx, parse_tcx


class ActivityTrackNotFoundError(Exception):
    pass


def _detect_format(blob: bytes, hint: str | None) -> str:
    if hint:
        h = hint.lower()
        if h in ("fit", "gpx", "tcx"):
            return h
    # FIT files start with a 12/14-byte header; magic ".FIT" lives at offset 8-12.
    if len(blob) > 12 and blob[8:12] == b".FIT":
        return "fit"
    head = blob.lstrip()[:512]
    if head[:5] == b"<?xml":
        if b"TrainingCenterDatabase" in head:
            return "tcx"
        return "gpx"
    raise ValueError("could not detect format; pass format=fit|gpx|tcx explicitly")


def _resolve_event_record(db: DbSession, user_id: UUID, workout_id: UUID) -> EventRecord:
    """Find the event_record belonging to a user, by id."""
    stmt = (
        select(EventRecord)
        .join(DataSource, EventRecord.data_source_id == DataSource.id)
        .where(EventRecord.id == workout_id, DataSource.user_id == user_id)
    )
    try:
        return db.execute(stmt).scalar_one()
    except NoResultFound as e:
        raise ActivityTrackNotFoundError(f"workout {workout_id} not found for user {user_id}") from e


def upsert_track_from_bytes(
    db: DbSession,
    user_id: UUID,
    workout_id: UUID,
    blob: bytes,
    format_hint: str | None = None,
) -> ActivityTrack:
    """Parse the file blob and write/replace the activity_track row for the given workout."""
    fmt = _detect_format(blob, format_hint)
    parsed: ParsedTrack
    if fmt == "fit":
        parsed = parse_fit(blob)
    elif fmt == "gpx":
        parsed = parse_gpx(blob)
    elif fmt == "tcx":
        parsed = parse_tcx(blob)
    else:
        raise ValueError(f"unsupported format: {fmt}")

    event = _resolve_event_record(db, user_id, workout_id)

    # Replace existing track row, if any. Use the polymorphic detail key 'track'.
    existing = db.execute(
        select(ActivityTrack).where(ActivityTrack.record_id == event.id)
    ).scalar_one_or_none()
    if existing is not None:
        db.delete(existing)
        db.flush()
    # Need a row in event_record_detail with matching detail_type for the polymorphic mapper.
    # ActivityTrack inherits from EventRecordDetail, so a single insert covers both.

    bbox = parsed.bbox or (None, None, None, None)
    track = ActivityTrack(
        record_id=event.id,
        sample_count=parsed.sample_count,
        distance_meters=Decimal(str(parsed.distance_meters)) if parsed.distance_meters is not None else None,
        bbox_min_lat=Decimal(str(bbox[0])) if bbox[0] is not None else None,
        bbox_min_lon=Decimal(str(bbox[1])) if bbox[1] is not None else None,
        bbox_max_lat=Decimal(str(bbox[2])) if bbox[2] is not None else None,
        bbox_max_lon=Decimal(str(bbox[3])) if bbox[3] is not None else None,
        elevation_gain_meters=Decimal(str(parsed.elevation_gain_meters)) if parsed.elevation_gain_meters is not None else None,
        elevation_loss_meters=Decimal(str(parsed.elevation_loss_meters)) if parsed.elevation_loss_meters is not None else None,
        source_format=parsed.source_format,
        track_points=parsed.track_points,
        streams=parsed.streams,
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


def get_track(db: DbSession, user_id: UUID, workout_id: UUID) -> ActivityTrack:
    event = _resolve_event_record(db, user_id, workout_id)
    track = db.execute(
        select(ActivityTrack).where(ActivityTrack.record_id == event.id)
    ).scalar_one_or_none()
    if track is None:
        raise ActivityTrackNotFoundError(f"no track for workout {workout_id}")
    return track


def delete_track(db: DbSession, user_id: UUID, workout_id: UUID) -> None:
    track = get_track(db, user_id, workout_id)
    db.delete(track)
    db.commit()
