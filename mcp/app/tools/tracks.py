"""MCP tools for activity tracks and per-sample sensor streams (FIT/GPX-derived)."""

import logging

from fastmcp import FastMCP

from app.services.api_client import client

logger = logging.getLogger(__name__)

tracks_router = FastMCP(name="Activity Track Tools")


@tracks_router.tool
async def get_workout_track(user_id: str, workout_id: str, format: str = "geojson") -> dict:
    """
    Get the GPS track for a single workout.

    Returns either a GeoJSON LineString (default) or the raw track points and
    bounding box. Tracks are populated by uploading a Garmin .fit / .gpx file
    via /events/workouts/{id}/track.

    Args:
        user_id: UUID of the user. Use get_users to discover available users.
        workout_id: UUID of the workout. Use get_workout_events to find workouts.
        format: 'geojson' (default) or 'raw' for unencoded track_points list.

    Returns:
        format='geojson': a GeoJSON Feature with geometry.type=LineString and properties
            (sample_count, distance_meters, elevation_gain_meters, elevation_loss_meters).
        format='raw': dict with sample_count, distance_meters, bbox (min_lat,min_lon,max_lat,max_lon),
            elevation gain/loss, source_format ('fit'|'gpx'|'tcx'), track_points, streams (names only).

    Notes:
        - 404 means no track has been uploaded for this workout.
        - track_points entries: {t: offset_seconds_from_start, lat, lon, ele}.
        - For per-sample HR/power/cadence, call get_workout_streams.
    """
    try:
        return await client.get_workout_track(user_id, workout_id, format=format)
    except Exception as e:
        return {"error": "Failed to fetch workout track", "details": str(e)}


@tracks_router.tool
async def get_workout_streams(user_id: str, workout_id: str, fields: str | None = None) -> dict:
    """
    Get per-sample sensor streams for a workout (heart_rate, power, cadence, speed, temperature).

    Streams come from the FIT/GPX uploaded for this workout. Each stream is a list
    of [t_offset_seconds, value] pairs at the file's native sample rate (typically 1Hz).

    Args:
        user_id: UUID of the user.
        workout_id: UUID of the workout.
        fields: Optional comma-separated stream names to include
            (e.g. "heart_rate,power"). Default = all available.

    Returns:
        {
            "workout_id": "...",
            "sample_count": 3600,
            "streams": {
                "heart_rate": [[0.0, 122], [1.0, 124], ...],
                "power":      [[0.0, 180], ...],
                ...
            }
        }

    Notes:
        - 404 means no track/streams have been uploaded for this workout.
        - Common stream names: heart_rate, power, cadence, speed, temperature.
        - Power is typically only present for cycling activities with a power meter.
    """
    try:
        return await client.get_workout_streams(user_id, workout_id, fields=fields)
    except Exception as e:
        return {"error": "Failed to fetch workout streams", "details": str(e)}
