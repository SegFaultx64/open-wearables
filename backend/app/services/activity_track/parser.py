"""FIT and GPX parsers.

Returns a ParsedTrack with track_points (lat/lon/ele/t) and streams
(heart_rate, power, cadence, speed, temperature, distance) keyed by t (offset_seconds).

Streams are sparse: only sensors that the file actually recorded are present.
Point/stream sample rate is whatever the file was recorded at (typically 1Hz for
FIT, 1Hz or per-trackpoint for GPX).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET


@dataclass
class ParsedTrack:
    source_format: str  # "fit" | "gpx" | "tcx"
    start_time: datetime | None = None
    sample_count: int = 0
    distance_meters: float | None = None
    bbox: tuple[float, float, float, float] | None = None  # (min_lat, min_lon, max_lat, max_lon)
    elevation_gain_meters: float | None = None
    elevation_loss_meters: float | None = None
    track_points: list[dict[str, Any]] = field(default_factory=list)  # {t, lat, lon, ele}
    streams: dict[str, list[list[float]]] = field(default_factory=dict)  # name -> [[t, value], ...]


def _bbox_and_elev(track_points: list[dict[str, Any]]) -> tuple[
    tuple[float, float, float, float] | None,
    float | None,
    float | None,
]:
    lats = [p["lat"] for p in track_points if p.get("lat") is not None]
    lons = [p["lon"] for p in track_points if p.get("lon") is not None]
    eles = [p["ele"] for p in track_points if p.get("ele") is not None]
    bbox = (min(lats), min(lons), max(lats), max(lons)) if lats and lons else None
    gain = loss = None
    if len(eles) >= 2:
        gain = sum(max(0.0, b - a) for a, b in zip(eles, eles[1:]))
        loss = sum(max(0.0, a - b) for a, b in zip(eles, eles[1:]))
    return bbox, gain, loss


def parse_fit(data: bytes) -> ParsedTrack:
    """Parse a Garmin .fit file. Requires `fitparse` at runtime."""
    from fitparse import FitFile  # local import to avoid hard dep at import time

    fit = FitFile(BytesIO(data))
    parsed = ParsedTrack(source_format="fit")

    points: list[dict[str, Any]] = []
    streams: dict[str, list[list[float]]] = {}

    SEMICIRCLES_TO_DEG = 180.0 / (2**31)
    start_ts: float | None = None
    last_distance: float | None = None

    def _stream(name: str) -> list[list[float]]:
        return streams.setdefault(name, [])

    for record in fit.get_messages("record"):
        values = {f.name: f.value for f in record.fields}
        ts = values.get("timestamp")
        if ts is None:
            continue
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts_s = ts.timestamp()
        else:
            ts_s = float(ts)
        if start_ts is None:
            start_ts = ts_s
            parsed.start_time = datetime.fromtimestamp(ts_s, tz=timezone.utc)
        t = round(ts_s - start_ts, 3)

        lat_sc = values.get("position_lat")
        lon_sc = values.get("position_long")
        ele = values.get("enhanced_altitude") or values.get("altitude")
        lat = lat_sc * SEMICIRCLES_TO_DEG if lat_sc is not None else None
        lon = lon_sc * SEMICIRCLES_TO_DEG if lon_sc is not None else None
        if lat is not None and lon is not None:
            points.append({"t": t, "lat": lat, "lon": lon, "ele": float(ele) if ele is not None else None})

        for src_field, stream_name in (
            ("heart_rate", "heart_rate"),
            ("power", "power"),
            ("cadence", "cadence"),
            ("enhanced_speed", "speed"),
            ("speed", "speed"),
            ("temperature", "temperature"),
        ):
            v = values.get(src_field)
            if v is None:
                continue
            arr = _stream(stream_name)
            # avoid duplicate entries when both speed and enhanced_speed are present
            if arr and arr[-1][0] == t:
                continue
            arr.append([t, float(v)])

        last_distance = values.get("distance") or last_distance

    parsed.track_points = points
    parsed.streams = streams
    parsed.sample_count = len(points)
    parsed.distance_meters = float(last_distance) if last_distance is not None else None
    bbox, gain, loss = _bbox_and_elev(points)
    parsed.bbox = bbox
    parsed.elevation_gain_meters = gain
    parsed.elevation_loss_meters = loss
    return parsed


def parse_gpx(data: bytes) -> ParsedTrack:
    parsed = ParsedTrack(source_format="gpx")
    ns = {"gpx": "http://www.topografix.com/GPX/1/1", "ns3": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"}
    root = ET.fromstring(data)
    # support both namespaced and non-namespaced GPX
    if root.tag.startswith("{"):
        ns["gpx"] = root.tag.split("}")[0][1:]

    points: list[dict[str, Any]] = []
    streams: dict[str, list[list[float]]] = {}
    start_ts: float | None = None

    for trkpt in root.iter(f"{{{ns['gpx']}}}trkpt"):
        lat = float(trkpt.attrib["lat"]) if "lat" in trkpt.attrib else None
        lon = float(trkpt.attrib["lon"]) if "lon" in trkpt.attrib else None
        ele_el = trkpt.find(f"{{{ns['gpx']}}}ele")
        time_el = trkpt.find(f"{{{ns['gpx']}}}time")
        ele = float(ele_el.text) if ele_el is not None and ele_el.text else None
        ts: float | None = None
        if time_el is not None and time_el.text:
            try:
                dt = datetime.fromisoformat(time_el.text.replace("Z", "+00:00"))
                ts = dt.timestamp()
                if start_ts is None:
                    start_ts = ts
                    parsed.start_time = dt
            except ValueError:
                pass
        t = round((ts - start_ts), 3) if (ts is not None and start_ts is not None) else float(len(points))

        if lat is not None and lon is not None:
            points.append({"t": t, "lat": lat, "lon": lon, "ele": ele})

        # Garmin TrackPointExtension: <gpxtpx:hr>, <gpxtpx:cad>, <gpxtpx:atemp>
        for ext in trkpt.iter():
            tag = ext.tag.rsplit("}", 1)[-1].lower()
            if tag in ("hr", "heartrate") and ext.text:
                streams.setdefault("heart_rate", []).append([t, float(ext.text)])
            elif tag in ("cad", "cadence") and ext.text:
                streams.setdefault("cadence", []).append([t, float(ext.text)])
            elif tag in ("power", "watts") and ext.text:
                streams.setdefault("power", []).append([t, float(ext.text)])
            elif tag in ("atemp", "temperature") and ext.text:
                streams.setdefault("temperature", []).append([t, float(ext.text)])

    parsed.track_points = points
    parsed.streams = streams
    parsed.sample_count = len(points)
    bbox, gain, loss = _bbox_and_elev(points)
    parsed.bbox = bbox
    parsed.elevation_gain_meters = gain
    parsed.elevation_loss_meters = loss
    return parsed
