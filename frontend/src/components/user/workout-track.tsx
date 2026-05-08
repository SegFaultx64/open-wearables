import { useEffect, useMemo, useRef, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { useWorkoutTrack, useWorkoutStreams } from '@/hooks/api/use-health';

interface WorkoutTrackProps {
  userId: string;
  workoutId: string;
}

interface LeafletNS {
  map: (el: HTMLElement, opts?: Record<string, unknown>) => any;
  tileLayer: (urlTemplate: string, opts?: Record<string, unknown>) => any;
  polyline: (latlngs: number[][], opts?: Record<string, unknown>) => any;
  latLngBounds: (sw: [number, number], ne: [number, number]) => any;
  Map?: unknown;
}

let leafletPromise: Promise<LeafletNS> | null = null;
function loadLeaflet(): Promise<LeafletNS> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('Leaflet only loads in the browser'));
  }
  if (leafletPromise) return leafletPromise;
  leafletPromise = (async () => {
    // CSS first
    if (!document.querySelector('link[data-leaflet-css]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      link.setAttribute('data-leaflet-css', '');
      link.crossOrigin = '';
      document.head.appendChild(link);
    }
    const mod = await import('leaflet');
    return (mod.default ?? mod) as unknown as LeafletNS;
  })();
  return leafletPromise;
}

export function WorkoutTrack({ userId, workoutId }: WorkoutTrackProps) {
  const { data: track, isLoading: trackLoading, error: trackError } =
    useWorkoutTrack(userId, workoutId);
  const { data: streams } = useWorkoutStreams(userId, workoutId);

  const mapDivRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any>(null);
  const [mapErr, setMapErr] = useState<string | null>(null);

  // Build chart data: align HR / power / cadence by t-offset bucket
  const chartData = useMemo(() => {
    const s = streams?.streams || {};
    const buckets = new Map<number, { t: number; hr?: number; power?: number; cadence?: number; speed?: number }>();
    const sample = (name: string, key: 'hr' | 'power' | 'cadence' | 'speed') => {
      for (const [t, v] of (s[name] || []) as [number, number][]) {
        const tb = Math.round(t);
        const b = buckets.get(tb) ?? { t: tb };
        b[key] = v;
        buckets.set(tb, b);
      }
    };
    sample('heart_rate', 'hr');
    sample('power', 'power');
    sample('cadence', 'cadence');
    sample('speed', 'speed');
    return [...buckets.values()].sort((a, b) => a.t - b.t);
  }, [streams]);

  // Mount Leaflet and draw polyline once track + container are both ready
  useEffect(() => {
    if (!mapDivRef.current || !track) return;
    const coords = (track.geometry?.coordinates || []) as number[][];
    if (coords.length < 2) return;
    let cancelled = false;
    let map: any = null;
    loadLeaflet()
      .then((L) => {
        if (cancelled || !mapDivRef.current) return;
        // [lon, lat, ele?] -> [lat, lon]
        const latlngs = coords.map((c) => [c[1], c[0]] as [number, number]);
        map = L.map(mapDivRef.current, { zoomControl: true, attributionControl: false });
        L.tileLayer(
          'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          { maxZoom: 19, subdomains: ['a', 'b', 'c'] }
        ).addTo(map);
        const poly = L.polyline(latlngs, { color: '#22d3ee', weight: 3, opacity: 0.9 }).addTo(map);
        // fit bounds
        const lats = latlngs.map((c) => c[0]);
        const lons = latlngs.map((c) => c[1]);
        const bounds = L.latLngBounds(
          [Math.min(...lats), Math.min(...lons)],
          [Math.max(...lats), Math.max(...lons)],
        );
        map.fitBounds(bounds, { padding: [12, 12] });
        mapInstanceRef.current = map;
        // workaround Leaflet sizing in flex/grid containers
        setTimeout(() => map.invalidateSize?.(), 50);
      })
      .catch((e: Error) => {
        if (!cancelled) setMapErr(e.message || 'Failed to load map');
      });
    return () => {
      cancelled = true;
      try {
        mapInstanceRef.current?.remove?.();
      } catch {}
      mapInstanceRef.current = null;
    };
  }, [track]);

  if (trackLoading) {
    return (
      <div className="h-[260px] flex items-center justify-center">
        <div className="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (trackError) {
    return (
      <p className="text-xs text-muted-foreground text-center py-4">
        No GPS track available for this workout.
      </p>
    );
  }

  const props = track?.properties;
  const hasCoords = (track?.geometry?.coordinates?.length ?? 0) > 1;

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-3">
        <span>Track</span>
        {props && (
          <span className="text-[11px] text-muted-foreground/70 font-normal normal-case tracking-normal">
            {props.sample_count ?? 0} samples
            {props.distance_meters != null && (
              <> · {(props.distance_meters / 1000).toFixed(2)} km</>
            )}
            {props.elevation_gain_meters != null && (
              <> · ↑ {Math.round(props.elevation_gain_meters)}m</>
            )}
            {props.elevation_loss_meters != null && (
              <> · ↓ {Math.round(props.elevation_loss_meters)}m</>
            )}
            {props.source_format && <> · {props.source_format.toUpperCase()}</>}
          </span>
        )}
      </h4>

      {mapErr ? (
        <p className="text-xs text-rose-400">Map error: {mapErr}</p>
      ) : hasCoords ? (
        <div
          ref={mapDivRef}
          className="h-[280px] rounded-md overflow-hidden border border-border/60 bg-muted"
        />
      ) : (
        <p className="text-xs text-muted-foreground">
          No GPS coordinates in this track (indoor workout?).
        </p>
      )}

      {chartData.length > 1 && (
        <div>
          <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
            Streams
          </h5>
          <div className="h-[180px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ left: 8, right: 8, top: 4, bottom: 0 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis
                  dataKey="t"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: '#71717a', fontSize: 10 }}
                  tickFormatter={(v: number) => {
                    const m = Math.floor(v / 60);
                    const s = Math.floor(v % 60);
                    return s ? `${m}:${s.toString().padStart(2, '0')}` : `${m}m`;
                  }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: '#71717a', fontSize: 10 }}
                  width={32}
                />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(0,0,0,0.85)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    fontSize: 12,
                  }}
                  labelFormatter={(v: number) => `t=${v}s`}
                />
                {chartData[0]?.hr !== undefined && (
                  <Line type="monotone" dataKey="hr" stroke="#fb7185" strokeWidth={2} dot={false} name="HR" />
                )}
                {chartData[0]?.power !== undefined && (
                  <Line type="monotone" dataKey="power" stroke="#fbbf24" strokeWidth={2} dot={false} name="Power (W)" />
                )}
                {chartData[0]?.cadence !== undefined && (
                  <Line type="monotone" dataKey="cadence" stroke="#a78bfa" strokeWidth={2} dot={false} name="Cadence" />
                )}
                {chartData[0]?.speed !== undefined && (
                  <Line type="monotone" dataKey="speed" stroke="#22d3ee" strokeWidth={2} dot={false} name="Speed (m/s)" />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
