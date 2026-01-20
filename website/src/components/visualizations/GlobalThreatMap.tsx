import { useEffect, useRef, useState } from 'preact/hooks';
import type L from 'leaflet';

export interface MapEvent {
  id: string;
  lat: number;
  lng: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  label: string;
  color?: string;
  sourceLabel?: string;
  time?: string;
  location?: string;
  detail?: string;
  url?: string;
}

interface GlobalThreatMapProps {
  events: MapEvent[];
  loading: boolean;
  statusText: string;
  scopeLabel?: string;
  selectedId?: string;
  onSelect?: (event: MapEvent) => void;
  panelMode?: 'anchor' | 'corner';
  onPanelModeChange?: (mode: 'anchor' | 'corner') => void;
  onClearSelection?: () => void;
}

// Standardized severity colors matching design tokens
const SEVERITY_COLORS = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
} as const;

const SEVERITY_RADIUS = {
  critical: 12,
  high: 10,
  medium: 8,
  low: 6,
} as const;

const getSeverityColor = (severity: MapEvent['severity']) => {
  return SEVERITY_COLORS[severity] || SEVERITY_COLORS.medium;
};

// India bounds
const INDIA_BOUNDS: [[number, number], [number, number]] = [[6, 68], [36, 98]];
const WORLD_BOUNDS: [[number, number], [number, number]] = [[-60, -180], [80, 180]];

export default function GlobalThreatMap(props: GlobalThreatMapProps) {
  const { events, loading, statusText, scopeLabel, selectedId, onSelect, panelMode = 'anchor', onPanelModeChange, onClearSelection } = props;
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const leafletRef = useRef<typeof L | null>(null);
  const markersRef = useRef<Map<string, L.CircleMarker>>(new Map());
  const [localSelectedId, setLocalSelectedId] = useState<string | null>(null);
  const [hoverInfo, setHoverInfo] = useState<{ event: MapEvent; x: number; y: number } | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  const activeId = selectedId ?? localSelectedId;
  const activeEvent = events.find(event => event.id === activeId);

  useEffect(() => {
    if (selectedId) setLocalSelectedId(selectedId);
  }, [selectedId]);

  const formatTime = (value?: string) => {
    if (!value) return '—';
    const parsed = Date.parse(value);
    if (Number.isNaN(parsed)) return value;
    return new Date(parsed).toISOString().replace('T', ' ').replace('Z', ' UTC');
  };

  // Dynamically import Leaflet on client side only
  useEffect(() => {
    if (typeof window === 'undefined') return;

    let mounted = true;

    const initMap = async () => {
      try {
        // Dynamically import Leaflet and its CSS
        const [leafletModule] = await Promise.all([
          import('leaflet'),
          import('leaflet/dist/leaflet.css'),
        ]);

        if (!mounted || !mapContainerRef.current || mapRef.current) return;

        const L = leafletModule.default;
        leafletRef.current = L;

        const map = L.map(mapContainerRef.current, {
          center: [20, 78], // Center on India
          zoom: 4,
          minZoom: 2,
          maxZoom: 18,
          zoomControl: false,
          attributionControl: true,
        });

        // CartoDB Dark Matter tiles (dark theme)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
          subdomains: 'abcd',
          maxZoom: 20,
        }).addTo(map);

        // Add zoom control to bottom-left
        L.control.zoom({ position: 'bottomleft' }).addTo(map);

        mapRef.current = map;
        setMapReady(true);
      } catch (error) {
        console.error('Failed to load map:', error);
        setMapError(error instanceof Error ? error.message : 'Failed to load map');
      }
    };

    initMap();

    // Cleanup on unmount
    return () => {
      mounted = false;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
      setMapReady(false);
    };
  }, []);

  // Handle scope changes (India vs Global)
  useEffect(() => {
    const map = mapRef.current;
    const L = leafletRef.current;
    if (!map || !L || !mapReady) return;

    if (scopeLabel === 'INDIA') {
      map.fitBounds(INDIA_BOUNDS, { padding: [20, 20], maxZoom: 5 });
    } else {
      // Fit to event bounds or world view
      if (events.length > 0) {
        const eventBounds = L.latLngBounds(
          events.map(e => [e.lat, e.lng] as [number, number])
        );
        map.fitBounds(eventBounds, { padding: [50, 50], maxZoom: 5 });
      } else {
        map.fitBounds(WORLD_BOUNDS, { padding: [20, 20] });
      }
    }
  }, [scopeLabel, events.length, mapReady]);

  // Update markers when events change
  useEffect(() => {
    const map = mapRef.current;
    const L = leafletRef.current;
    if (!map || !L || !mapReady) return;

    // Clear existing markers
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current.clear();

    // Add new markers
    events.forEach(event => {
      if (!Number.isFinite(event.lat) || !Number.isFinite(event.lng)) return;

      const color = event.color || getSeverityColor(event.severity);
      const radius = SEVERITY_RADIUS[event.severity] || 8;

      // Add glow effect first (so it's behind the main marker)
      const glowMarker = L.circleMarker([event.lat, event.lng], {
        radius: radius * 2.5,
        fillColor: color,
        fillOpacity: 0.15,
        stroke: false,
      }).addTo(map);

      const marker = L.circleMarker([event.lat, event.lng], {
        radius,
        fillColor: color,
        fillOpacity: 0.7,
        color: color,
        weight: 2,
        opacity: 0.9,
      }).addTo(map);

      // Click handler
      marker.on('click', () => {
        setLocalSelectedId(event.id);
        onSelect?.(event);
      });

      // Hover handlers
      marker.on('mouseover', () => {
        const containerPoint = map.latLngToContainerPoint([event.lat, event.lng]);
        setHoverInfo({
          event,
          x: containerPoint.x,
          y: containerPoint.y,
        });
        marker.setStyle({ weight: 3, fillOpacity: 0.9 });
      });

      marker.on('mouseout', () => {
        setHoverInfo(null);
        marker.setStyle({ weight: 2, fillOpacity: 0.7 });
      });

      markersRef.current.set(event.id, marker);
      markersRef.current.set(`${event.id}-glow`, glowMarker);
    });

    return () => {
      markersRef.current.forEach(marker => marker.remove());
      markersRef.current.clear();
    };
  }, [events, onSelect, mapReady]);

  // Highlight selected marker
  useEffect(() => {
    if (!mapReady) return;

    markersRef.current.forEach((marker, id) => {
      if (id.endsWith('-glow')) return;

      const event = events.find(e => e.id === id);
      if (!event) return;

      const color = event.color || getSeverityColor(event.severity);
      const isSelected = id === activeId;

      marker.setStyle({
        weight: isSelected ? 4 : 2,
        fillOpacity: isSelected ? 1 : 0.7,
        color: isSelected ? '#ffffff' : color,
      });

      if (isSelected) {
        marker.bringToFront();
      }
    });
  }, [activeId, events, mapReady]);

  const severityTextClass = (severity: MapEvent['severity']) => {
    switch (severity) {
      case 'critical': return 'text-red-400';
      case 'high': return 'text-orange-400';
      case 'medium': return 'text-yellow-400';
      case 'low': return 'text-emerald-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div class="relative h-full w-full bg-neutral-950 overflow-hidden">
      {/* Leaflet Map Container */}
      <div
        ref={mapContainerRef}
        class="absolute inset-0 z-10"
        style={{ background: '#0a0a0a' }}
      />

      {/* Map Loading Indicator */}
      {!mapReady && !mapError && (
        <div class="absolute inset-0 z-20 flex items-center justify-center bg-neutral-950">
          <div class="text-center">
            <div class="w-8 h-8 border-2 border-neutral-700 border-t-white rounded-full animate-spin mx-auto mb-3"></div>
            <div class="text-xs text-gray-500 font-mono">LOADING MAP...</div>
          </div>
        </div>
      )}

      {/* Map Error State */}
      {mapError && (
        <div class="absolute inset-0 z-20 flex items-center justify-center bg-neutral-950">
          <div class="text-center max-w-md px-4">
            <div class="text-red-500 text-2xl mb-3">⚠</div>
            <div class="text-sm text-red-400 font-mono mb-2">MAP LOAD FAILED</div>
            <div class="text-xs text-gray-500 font-mono">{mapError}</div>
            <button
              type="button"
              onClick={() => window.location.reload()}
              class="mt-4 px-4 py-2 text-xs font-mono bg-neutral-800 text-white border border-neutral-700 rounded hover:bg-neutral-700 transition-colors"
            >
              RETRY
            </button>
          </div>
        </div>
      )}

      {/* Legend */}
      <div class="absolute bottom-4 left-4 z-30 bg-black/90 backdrop-blur border border-neutral-800 rounded p-3 text-xs font-mono pointer-events-none">
        <div class="font-bold text-white mb-2 text-xs">THREAT LEGEND</div>
        <div class="space-y-1">
          <div class="flex items-center gap-2 text-gray-400">
            <span class="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_4px_#dc2626]"></span>
            <span class="text-red-400">Critical</span>
          </div>
          <div class="flex items-center gap-2 text-gray-400">
            <span class="w-2 h-2 rounded-full bg-orange-500 shadow-[0_0_4px_#f97316]"></span>
            <span class="text-orange-400">High</span>
          </div>
          <div class="flex items-center gap-2 text-gray-400">
            <span class="w-2 h-2 rounded-full bg-yellow-500 shadow-[0_0_4px_#eab308]"></span>
            <span class="text-yellow-400">Medium</span>
          </div>
          <div class="flex items-center gap-2 text-gray-400">
            <span class="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_4px_#22c55e]"></span>
            <span class="text-emerald-400">Low</span>
          </div>
        </div>
      </div>

      {/* Status Panel */}
      <div class="absolute top-4 right-4 z-30 bg-black/90 backdrop-blur border border-neutral-800 rounded p-3 text-right font-mono pointer-events-none">
        <div class="text-sm font-bold text-white">THREAT MONITOR</div>
        <div class={`text-lg font-bold mt-1 ${loading ? 'text-yellow-400' : 'text-red-400'}`}>
          {loading ? 'SYNCING...' : `${events.length} ACTIVE`}
        </div>
        <div class="text-[10px] text-gray-500 mt-1">{statusText}</div>
        {scopeLabel && <div class="text-[10px] text-gray-400 mt-1">SCOPE: {scopeLabel}</div>}
      </div>

      {/* Event Detail Panel */}
      {activeEvent ? (
        <div
          class="absolute z-40 w-[280px] max-w-[280px] bg-black/95 border border-neutral-800 rounded-lg p-3"
          style={{
            right: panelMode === 'corner' ? '16px' : undefined,
            bottom: panelMode === 'corner' ? '16px' : undefined,
            left: panelMode === 'anchor' ? '300px' : undefined,
            top: panelMode === 'anchor' ? '16px' : undefined,
          }}
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-[10px] text-gray-500 uppercase tracking-widest">
              {activeEvent.sourceLabel || 'SOURCE'}
            </span>
            <div class="flex gap-1">
              <button
                type="button"
                onClick={() => onPanelModeChange?.(panelMode === 'anchor' ? 'corner' : 'anchor')}
                class="px-2 py-0.5 text-[10px] text-gray-500 border border-neutral-700 rounded hover:text-white hover:border-neutral-600 transition-colors"
              >
                {panelMode === 'anchor' ? 'DOCK' : 'ANCHOR'}
              </button>
              <button
                type="button"
                onClick={() => onClearSelection?.()}
                class="px-2 py-0.5 text-[10px] text-gray-500 border border-neutral-700 rounded hover:text-white hover:border-neutral-600 transition-colors"
              >
                CLOSE
              </button>
            </div>
          </div>
          <div class="font-bold text-white text-sm">{activeEvent.label}</div>
          <div class="mt-1 text-xs text-gray-500">{formatTime(activeEvent.time)}</div>
          <div class={`mt-1 text-xs ${severityTextClass(activeEvent.severity)} uppercase`}>
            {activeEvent.severity}
          </div>
          {activeEvent.location && (
            <div class="mt-1 text-xs text-gray-400">{activeEvent.location}</div>
          )}
          {activeEvent.detail && (
            <div class="mt-2 text-xs text-gray-400 leading-relaxed">{activeEvent.detail}</div>
          )}
          {activeEvent.url && (
            <a
              href={activeEvent.url}
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex mt-3 px-3 py-1.5 bg-white text-black font-bold text-xs rounded hover:bg-gray-200 transition-colors"
            >
              View Source
            </a>
          )}
        </div>
      ) : (
        <div class="absolute right-4 bottom-4 z-40 bg-black/80 border border-neutral-800 rounded px-3 py-2 text-xs text-gray-500 pointer-events-none">
          Click a marker for details
        </div>
      )}

      {/* Hover Tooltip */}
      {hoverInfo && (
        <div
          class="absolute z-50 bg-black/90 border border-neutral-700 rounded px-2 py-1.5 text-xs pointer-events-none max-w-[200px]"
          style={{ left: hoverInfo.x + 16, top: hoverInfo.y + 16 }}
        >
          <div class="font-bold text-white">{hoverInfo.event.label}</div>
          <div class="text-gray-500 mt-0.5">
            {hoverInfo.event.sourceLabel || 'Source'} · {formatTime(hoverInfo.event.time)}
          </div>
        </div>
      )}
    </div>
  );
}
