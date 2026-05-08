"""Activity track upload + retrieval.

POST /api/v1/users/{user_id}/events/workouts/{workout_id}/track
    multipart/form-data with `file` (FIT or GPX), optional `format` query param.
GET  /api/v1/users/{user_id}/events/workouts/{workout_id}/track
    returns the stored track. ?format=geojson returns a GeoJSON LineString.
GET  /api/v1/users/{user_id}/events/workouts/{workout_id}/streams
    returns the per-sample streams. Optional ?fields=heart_rate,power
DELETE /api/v1/users/{user_id}/events/workouts/{workout_id}/track
"""
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.database import DbSession
from app.services import ApiKeyDep
from app.services.activity_track import (
    ActivityTrackNotFoundError,
    delete_track,
    get_track,
    upsert_track_from_bytes,
)

router = APIRouter()


@router.post(
    "/users/{user_id}/events/workouts/{workout_id}/track",
    status_code=status.HTTP_201_CREATED,
    tags=["External: Activity Tracks"],
)
async def upload_track(
    user_id: UUID,
    workout_id: UUID,
    db: DbSession,
    _api_key: ApiKeyDep,
    file: UploadFile = File(..., description="FIT or GPX file"),
    format: str | None = Query(None, description="fit | gpx (override auto-detection)"),
) -> dict:
    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="empty file")
    try:
        track = upsert_track_from_bytes(db, user_id, workout_id, blob, format_hint=format)
    except ActivityTrackNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "workout_id": str(workout_id),
        "source_format": track.source_format,
        "sample_count": track.sample_count,
        "distance_meters": float(track.distance_meters) if track.distance_meters is not None else None,
        "elevation_gain_meters": float(track.elevation_gain_meters) if track.elevation_gain_meters is not None else None,
        "streams": list((track.streams or {}).keys()),
    }


def _to_geojson(track) -> dict:
    coords = [
        [p["lon"], p["lat"], p["ele"]] if p.get("ele") is not None else [p["lon"], p["lat"]]
        for p in (track.track_points or [])
        if p.get("lat") is not None and p.get("lon") is not None
    ]
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {
            "workout_id": str(track.record_id),
            "sample_count": track.sample_count,
            "distance_meters": float(track.distance_meters) if track.distance_meters is not None else None,
            "elevation_gain_meters": float(track.elevation_gain_meters) if track.elevation_gain_meters is not None else None,
            "elevation_loss_meters": float(track.elevation_loss_meters) if track.elevation_loss_meters is not None else None,
            "source_format": track.source_format,
        },
    }


@router.get(
    "/users/{user_id}/events/workouts/{workout_id}/track",
    tags=["External: Activity Tracks"],
)
def get_workout_track(
    user_id: UUID,
    workout_id: UUID,
    db: DbSession,
    _api_key: ApiKeyDep,
    format: str = Query("raw", description="raw | geojson"),
) -> dict:
    try:
        track = get_track(db, user_id, workout_id)
    except ActivityTrackNotFoundError:
        raise HTTPException(status_code=404, detail=f"no track for workout {workout_id}")
    if format == "geojson":
        return _to_geojson(track)
    return {
        "workout_id": str(workout_id),
        "source_format": track.source_format,
        "sample_count": track.sample_count,
        "distance_meters": float(track.distance_meters) if track.distance_meters is not None else None,
        "bbox": [
            float(track.bbox_min_lat) if track.bbox_min_lat is not None else None,
            float(track.bbox_min_lon) if track.bbox_min_lon is not None else None,
            float(track.bbox_max_lat) if track.bbox_max_lat is not None else None,
            float(track.bbox_max_lon) if track.bbox_max_lon is not None else None,
        ],
        "elevation_gain_meters": float(track.elevation_gain_meters) if track.elevation_gain_meters is not None else None,
        "elevation_loss_meters": float(track.elevation_loss_meters) if track.elevation_loss_meters is not None else None,
        "track_points": track.track_points or [],
        "streams": list((track.streams or {}).keys()),
    }


@router.get(
    "/users/{user_id}/events/workouts/{workout_id}/streams",
    tags=["External: Activity Tracks"],
)
def get_workout_streams(
    user_id: UUID,
    workout_id: UUID,
    db: DbSession,
    _api_key: ApiKeyDep,
    fields: str | None = Query(None, description="comma-separated list of stream names; default = all"),
) -> dict:
    try:
        track = get_track(db, user_id, workout_id)
    except ActivityTrackNotFoundError:
        raise HTTPException(status_code=404, detail=f"no track for workout {workout_id}")
    streams = track.streams or {}
    if fields:
        wanted = {f.strip() for f in fields.split(",") if f.strip()}
        streams = {k: v for k, v in streams.items() if k in wanted}
    return {
        "workout_id": str(workout_id),
        "sample_count": track.sample_count,
        "streams": streams,
    }


@router.delete(
    "/users/{user_id}/events/workouts/{workout_id}/track",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["External: Activity Tracks"],
)
def delete_workout_track(
    user_id: UUID,
    workout_id: UUID,
    db: DbSession,
    _api_key: ApiKeyDep,
) -> None:
    try:
        delete_track(db, user_id, workout_id)
    except ActivityTrackNotFoundError:
        raise HTTPException(status_code=404, detail=f"no track for workout {workout_id}")
