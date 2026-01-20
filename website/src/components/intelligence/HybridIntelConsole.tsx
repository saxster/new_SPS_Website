import { useEffect, useMemo, useState } from 'preact/hooks';
import GlobalThreatMap from '../visualizations/GlobalThreatMap';
import type { MapEvent } from '../visualizations/GlobalThreatMap';
import GdacsFeed from './GdacsFeed';
import CisaKevFeed from './CisaKevFeed';
import DomainRiskAssessment from './DomainRiskAssessment';
import { fetchJsonWithCache } from '../../utils/liveFetch';
import { classifyMagnitude, classifyAqi } from '../../utils/severityClassification';

const REFRESH_MS = 60000;
const CACHE_TTL_MS = 60000;

// Use server-side proxy to bypass CORS restrictions
const GDACS_ENDPOINT = '/api/intel-proxy?source=gdacs';
const USGS_ENDPOINT = '/api/intel-proxy?source=usgs';
const EONET_ENDPOINT = '/api/intel-proxy?source=eonet';
const SWPC_ENDPOINT = '/api/intel-proxy?source=swpc';
const AIR_QUALITY_ENDPOINT = '/api/intel-proxy?source=aqi';
const GDELT_ENDPOINT = 'https://api.gdeltproject.org/api/v2/geo/geo?query=(protest%20OR%20riot%20OR%20arrest%20OR%20"security%20force")%20sourcecountry:IN&mode=pointdata&format=geojson&timespan=24h&maxpoints=50';
const RANSOMWARE_ENDPOINT = 'https://raw.githubusercontent.com/joshhighet/ransomwatch/main/posts.json';
const NEWS_ENDPOINT = '/api/news-wire';

// Location data still needed for mapping AQI responses
const INDIA_AQI_LOCATIONS = [
  { name: 'Delhi', lat: 28.6139, lng: 77.209 },
  { name: 'Mumbai', lat: 19.076, lng: 72.8777 },
  { name: 'Bengaluru', lat: 12.9716, lng: 77.5946 },
  { name: 'Hyderabad', lat: 17.385, lng: 78.4867 },
  { name: 'Chennai', lat: 13.0827, lng: 80.2707 },
  { name: 'Kolkata', lat: 22.5726, lng: 88.3639 },
  { name: 'Ahmedabad', lat: 23.0225, lng: 72.5714 },
  { name: 'Pune', lat: 18.5204, lng: 73.8567 },
  { name: 'Jaipur', lat: 26.9124, lng: 75.7873 },
  { name: 'Lucknow', lat: 26.8467, lng: 80.9462 },
  { name: 'Surat', lat: 21.1702, lng: 72.8311 },
  { name: 'Chandigarh', lat: 30.7333, lng: 76.7794 },
];

type Severity = 'low' | 'medium' | 'high' | 'critical';

type SourceKey = 'gdacs' | 'usgs' | 'eonet' | 'aqi' | 'swpc' | 'gdelt' | 'ransom' | 'news';

interface IntelEvent {
  id: string;
  source: SourceKey;
  sourceLabel: string;
  title: string;
  time?: string;
  lat?: number;
  lng?: number;
  severity: Severity;
  location?: string;
  detail?: string;
  url?: string;
  tags?: string[];
}

const SOURCE_META: Record<SourceKey, { label: string; color: string }> = {
  gdacs: { label: 'GDACS', color: '#f97316' },
  usgs: { label: 'USGS Quakes', color: '#facc15' },
  eonet: { label: 'NASA EONET', color: '#fb7185' },
  aqi: { label: 'Air Quality', color: '#38bdf8' },
  swpc: { label: 'NOAA SWPC', color: '#a78bfa' },
  gdelt: { label: 'GDELT Unrest', color: '#ef4444' },
  ransom: { label: 'Cyber Breach', color: '#d946ef' },
  news: { label: 'SPS Wire', color: '#0ea5e9' }, // Cyan
};

const severityRank: Record<Severity, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

const formatUtc = (value?: string | number) => {
  if (value === undefined || value === null) return undefined;
  const parsed = typeof value === 'number' ? value : Date.parse(value);
  if (Number.isNaN(parsed)) return undefined;
  return new Date(parsed).toISOString();
};

const displayTime = (value?: string | number) => {
  if (!value) return '—';
  const parsed = typeof value === 'number' ? value : Date.parse(value);
  if (Number.isNaN(parsed)) return '—';
  return new Date(parsed).toISOString().replace('T', ' ').replace('Z', ' UTC');
};

const resolveTimeValue = (value?: string | number) => {
  if (!value) return 0;
  const parsed = typeof value === 'number' ? value : Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
};

const parseScaleSeverity = (message: string): Severity => {
  const match = message.match(/NOAA Scale:\s*([GSR])(\d)/i);
  if (!match) return 'medium';
  const scale = Number(match[2]);
  if (scale >= 4) return 'critical';
  if (scale === 3) return 'high';
  if (scale === 2) return 'medium';
  return 'low';
};

const pickLatestHourly = (times: string[], values: number[]) => {
  const now = Date.now();
  for (let i = times.length - 1; i >= 0; i -= 1) {
    const parsed = Date.parse(times[i]);
    if (!Number.isNaN(parsed) && parsed <= now) {
      return { time: times[i], value: values[i] };
    }
  }
  if (times.length === 0) return { time: undefined, value: undefined } as { time?: string; value?: number };
  return { time: times[times.length - 1], value: values[values.length - 1] };
};

// --- SOP ENGINE (The "Brain" of Sentinel) ---
const SOP_DATABASE: Record<string, string[]> = {
  // GENERIC DEFAULTS
  default_critical: [
    "ACTIVATE CRISIS MANAGEMENT TEAM (CMT) IMMEDIATELY.",
    "Conduct personnel headcount via safety app.",
    "Establish emergency comms channel (Satellite/Radio).",
    "Prepare for 72-hour lockdown."
  ],
  default_high: [
    "Notify Regional Security Manager (RSM).",
    "Review Business Continuity Plan (BCP) for this hazard.",
    "Check backup power and water reserves.",
    "Monitor local news channels for evacuation orders."
  ],
  default_medium: [
    "Issue advisory to local staff.",
    "Verify emergency contact lists are updated.",
    "Monitor situation for escalation."
  ],

  // SPECIFIC SOURCES
  usgs_critical: [ // Major Earthquake
    "IMMEDIATE EVACUATION to open ground.",
    "Isolate main gas and water lines immediately.",
    "Do NOT use elevators.",
    "Prepare for aftershocks (typically within 60 mins).",
    "Inspect structural pillars for cracks before re-entry."
  ],
  gdacs_flood: [
    "Relocate critical IT assets to Level 2 or higher.",
    "Deploy sandbags at entry points.",
    "Verify generator fuel levels (ensure 48h reserve).",
    "Identify safe evacuation routes avoiding low-lying areas."
  ],
  swpc_high: [ // Solar Storm
    "Disconnect non-essential grid-tied electronics.",
    "Switch GPS-dependent logistics to manual routing.",
    "Expect HF radio blackouts; switch to VHF/UHF.",
    "Monitor grid voltage stability."
  ],
  aqi_critical: [
    "Seal building envelope; activate positive pressure mode.",
    "Ensure all HVAC filters are HEPA grade.",
    "Suspend all outdoor labour and patrols.",
    "Distribute N95 masks to essential outdoor staff."
  ],
  gdelt_unrest: [ // Civil Unrest
    "Restrict facility access to Single Entry/Exit point.",
    "Activate 'Lockdown Mode' on access control systems.",
    "Remove company branding/signage from perimeter.",
    "Advise employees to work from home (WFH) until clear.",
    "Liaise with local Station House Officer (SHO)."
  ],
  ransom_breach: [ // Cyber Breach
    "BLOCK all connections to/from the affected vendor immediately.",
    "Scan own network for similar IOCs (Indicators of Compromise).",
    "Reset credentials for any shared accounts.",
    "Notify Legal and Compliance teams of potential exposure.",
    "Prepare 'Defensive Statement' for stakeholders."
  ],
  news_unrest: [ // News Wire Event (Protest/Riot)
    "Verify report with local police handle/control room.",
    "Identify proximity to own assets (within 5km?).",
    "Advise logistics fleet to reroute immediately.",
    "Monitor social media for crowd size estimates."
  ]
};

const getProtocols = (event: IntelEvent): string[] => {
  // 1. Try specific matches first
  if (event.source === 'usgs' && (event.severity === 'critical' || event.severity === 'high')) {
    return SOP_DATABASE.usgs_critical;
  }
  if (event.source === 'gdacs' && event.title.toLowerCase().includes('flood')) {
    return SOP_DATABASE.gdacs_flood;
  }
  if (event.source === 'swpc' && (event.severity === 'critical' || event.severity === 'high')) {
    return SOP_DATABASE.swpc_high;
  }
  if (event.source === 'aqi' && event.severity === 'critical') {
    return SOP_DATABASE.aqi_critical;
  }
  if (event.source === 'gdelt' && (event.title.includes('Protest') || event.title.includes('Riot'))) {
    return SOP_DATABASE.gdelt_unrest;
  }
  if (event.source === 'ransom') {
    return SOP_DATABASE.ransom_breach;
  }
  if (event.source === 'news' && (event.location === 'CIVIL UNREST' || event.location === 'PUBLIC SAFETY')) {
    return SOP_DATABASE.news_unrest;
  }

  // 2. Fallback to generic severity
  if (event.severity === 'critical') return SOP_DATABASE.default_critical;
  if (event.severity === 'high') return SOP_DATABASE.default_high;
  if (event.severity === 'medium') return SOP_DATABASE.default_medium;

  return [
    "Log event in Shift Report.",
    "Continue routine monitoring.",
    "No immediate action required."
  ];
};

export default function HybridIntelConsole() {
  const [events, setEvents] = useState<IntelEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [sourceStatus, setSourceStatus] = useState<Record<SourceKey, { status: 'live' | 'degraded'; updatedAt?: string }>>({
    gdacs: { status: 'degraded' },
    usgs: { status: 'degraded' },
    eonet: { status: 'degraded' },
    aqi: { status: 'degraded' },
    swpc: { status: 'degraded' },
    gdelt: { status: 'degraded' },
    ransom: { status: 'degraded' },
    news: { status: 'degraded' },
  });
  const [activeSources, setActiveSources] = useState<Record<SourceKey, boolean>>({
    gdacs: true,
    usgs: true,
    eonet: true,
    aqi: true,
    swpc: true,
    gdelt: true,
    ransom: true,
    news: true,
  });
  const [search, setSearch] = useState('');
  const [minSeverity, setMinSeverity] = useState<Severity>('low');
  const [focusIndia, setFocusIndia] = useState(true);
  const [selected, setSelected] = useState<IntelEvent | null>(null);
  const [showEventsPanel, setShowEventsPanel] = useState(true);
  const [autoRotate, setAutoRotate] = useState(true);
  const [spotlightIndex, setSpotlightIndex] = useState(0);
  const [panelMode, setPanelMode] = useState<'anchor' | 'corner'>('corner');
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    const load = async () => {
      const updatedAt = new Date().toISOString();
      const statuses: Record<SourceKey, { status: 'live' | 'degraded'; updatedAt?: string }> = {
        gdacs: { status: 'degraded' },
        usgs: { status: 'degraded' },
        eonet: { status: 'degraded' },
        aqi: { status: 'degraded' },
        swpc: { status: 'degraded' },
        gdelt: { status: 'degraded' },
        ransom: { status: 'degraded' },
        news: { status: 'degraded' },
      };
      const buckets: IntelEvent[] = [];

      const requests = await Promise.allSettled([
        fetchJsonWithCache<any>(GDACS_ENDPOINT, 'sps-gdacs-fusion', CACHE_TTL_MS, { signal: controller.signal }),
        fetchJsonWithCache<any>(USGS_ENDPOINT, 'sps-usgs-fusion', CACHE_TTL_MS, { signal: controller.signal }),
        fetchJsonWithCache<any>(EONET_ENDPOINT, 'sps-eonet-fusion', CACHE_TTL_MS, { signal: controller.signal }),
        fetchJsonWithCache<any>(AIR_QUALITY_ENDPOINT, 'sps-aqi-fusion', CACHE_TTL_MS, { signal: controller.signal }),
        fetchJsonWithCache<any>(SWPC_ENDPOINT, 'sps-swpc-fusion', CACHE_TTL_MS, { signal: controller.signal }),
        fetchJsonWithCache<any>(GDELT_ENDPOINT, 'sps-gdelt-fusion', CACHE_TTL_MS, { signal: controller.signal }),
        fetchJsonWithCache<any>(RANSOMWARE_ENDPOINT, 'sps-ransom-fusion', CACHE_TTL_MS, { signal: controller.signal }),
        fetchJsonWithCache<any>(NEWS_ENDPOINT, 'sps-news-fusion', 600000, { signal: controller.signal }), // 10 min cache for news
      ]);

      const [gdacsResult, usgsResult, eonetResult, aqiResult, swpcResult, gdeltResult, ransomResult, newsResult] = requests;

      if (gdacsResult.status === 'fulfilled') {
        const data = gdacsResult.value;
        const features = Array.isArray(data?.features) ? data.features : [];
        features.forEach((feature: any, index: number) => {
          const props = feature?.properties ?? {};
          const coords = feature?.geometry?.coordinates ?? [];
          const lng = Number(coords?.[0]);
          const lat = Number(coords?.[1]);
          if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
          const alert = String(props.alertlevel || props.alertLevel || '').toLowerCase();
          const severity: Severity = alert.includes('red')
            ? 'critical'
            : alert.includes('orange')
            ? 'high'
            : alert.includes('yellow')
            ? 'medium'
            : 'low';
          buckets.push({
            id: `gdacs-${props.eventid || props.eventId || index}`,
            source: 'gdacs',
            sourceLabel: SOURCE_META.gdacs.label,
            title: props.eventname || props.name || 'GDACS Alert',
            time: formatUtc(props.lastupdate || props.fromdate || props.date || props.datetime),
            lat,
            lng,
            severity,
            location: props.country || props.countryname || props.countryName,
            detail: props.description,
            url: props.url || props.link,
          });
        });
        statuses.gdacs = { status: 'live', updatedAt };
      } else {
        statuses.gdacs = { status: 'degraded', updatedAt };
      }

      if (usgsResult.status === 'fulfilled') {
        const data = usgsResult.value;
        const features = Array.isArray(data?.features) ? data.features : [];
        features.forEach((feature: any) => {
          const coords = feature?.geometry?.coordinates ?? [];
          const lng = Number(coords?.[0]);
          const lat = Number(coords?.[1]);
          if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
          const props = feature?.properties ?? {};
          const mag = Number(props.mag || 0);
          buckets.push({
            id: `usgs-${feature?.id || `${lat}-${lng}`}`,
            source: 'usgs',
            sourceLabel: SOURCE_META.usgs.label,
            title: props.title || `M${mag.toFixed(1)} Earthquake`,
            time: formatUtc(props.time),
            lat,
            lng,
            severity: classifyMagnitude(mag),
            location: props.place,
            detail: props.type ? `Type: ${props.type}` : undefined,
            url: props.url,
            tags: mag ? [`M${mag.toFixed(1)}`] : undefined,
          });
        });
        statuses.usgs = { status: 'live', updatedAt };
      } else {
        statuses.usgs = { status: 'degraded', updatedAt };
      }

      if (eonetResult.status === 'fulfilled') {
        const data = eonetResult.value;
        const eventsList = Array.isArray(data?.events) ? data.events : [];
        eventsList.forEach((event: any) => {
          const geom = Array.isArray(event?.geometry) ? event.geometry : [];
          const latest = geom[geom.length - 1];
          const coords = latest?.coordinates;
          let lng: number | undefined;
          let lat: number | undefined;
          if (Array.isArray(coords) && typeof coords[0] === 'number') {
            lng = coords[0];
            lat = coords[1];
          } else if (Array.isArray(coords?.[0])) {
            lng = coords[0][0];
            lat = coords[0][1];
          }
          const categories = Array.isArray(event?.categories) ? event.categories : [];
          const category = categories[0]?.title || 'Event';
          const severity: Severity = category.toLowerCase().includes('volcano')
            ? 'high'
            : category.toLowerCase().includes('storm')
            ? 'high'
            : category.toLowerCase().includes('wild')
            ? 'medium'
            : 'low';

          buckets.push({
            id: `eonet-${event.id}`,
            source: 'eonet',
            sourceLabel: SOURCE_META.eonet.label,
            title: event.title || 'EONET Event',
            time: formatUtc(latest?.date),
            lat,
            lng,
            severity,
            location: category,
            url: event.link,
          });
        });
        statuses.eonet = { status: 'live', updatedAt };
      } else {
        statuses.eonet = { status: 'degraded', updatedAt };
      }

      if (aqiResult.status === 'fulfilled') {
        const data = aqiResult.value;
        const blocks = Array.isArray(data) ? data : [];
        blocks.forEach((block: any, index: number) => {
          const hourly = block?.hourly;
          const times = Array.isArray(hourly?.time) ? hourly.time : [];
          const aqiValues = Array.isArray(hourly?.us_aqi) ? hourly.us_aqi : [];
          const pmValues = Array.isArray(hourly?.pm2_5) ? hourly.pm2_5 : [];
          if (times.length === 0 || aqiValues.length === 0) return;
          const latestAqi = pickLatestHourly(times, aqiValues);
          const latestPm = pickLatestHourly(times, pmValues);
          const location = INDIA_AQI_LOCATIONS[index];
          const aqi = latestAqi.value ?? 0;
          buckets.push({
            id: `aqi-${location?.name ?? index}`,
            source: 'aqi',
            sourceLabel: SOURCE_META.aqi.label,
            title: `AQI ${aqi} • ${location?.name ?? 'City'}`,
            time: formatUtc(latestAqi.time),
            lat: location?.lat,
            lng: location?.lng,
            severity: classifyAqi(aqi),
            location: location?.name,
            detail: latestPm.value ? `PM2.5: ${latestPm.value.toFixed(1)} μg/m³` : undefined,
            tags: ['India Focus'],
          });
        });
        statuses.aqi = { status: 'live', updatedAt };
      } else {
        statuses.aqi = { status: 'degraded', updatedAt };
      }

      if (swpcResult.status === 'fulfilled') {
        const data = Array.isArray(swpcResult.value) ? swpcResult.value : [];
        data.slice(0, 12).forEach((alert: any, index: number) => {
          const message = String(alert?.message || '');
          const lines = message.split('\n').map(line => line.trim()).filter(Boolean);
          const headline = lines.find(line => line.startsWith('ALERT') || line.startsWith('WARNING') || line.startsWith('WATCH') || line.startsWith('CONTINUED ALERT') || line.startsWith('EXTENDED WARNING')) || lines[0];
          buckets.push({
            id: `swpc-${alert?.product_id || index}`,
            source: 'swpc',
            sourceLabel: SOURCE_META.swpc.label,
            title: headline || 'Space Weather Alert',
            time: formatUtc(alert?.issue_datetime),
            severity: parseScaleSeverity(message),
            location: 'GLOBAL',
            detail: lines.slice(0, 4).join(' • '),
          });
        });
        statuses.swpc = { status: 'live', updatedAt };
      } else {
        statuses.swpc = { status: 'degraded', updatedAt };
      }

      if (gdeltResult.status === 'fulfilled') {
        const data = gdeltResult.value;
        const features = Array.isArray(data?.features) ? data.features : [];
        features.forEach((feature: any) => {
           const props = feature?.properties || {};
           const coords = feature?.geometry?.coordinates;
           if (!coords || !coords[0] || !coords[1]) return;
           const name = props.name || 'Incident';
           const isCritical = name.toLowerCase().includes('armed') || name.toLowerCase().includes('riot');
           
           buckets.push({
              id: `gdelt-${Math.random()}`,
              source: 'gdelt',
              sourceLabel: SOURCE_META.gdelt.label,
              title: `${name} reported`,
              time: new Date().toISOString(),
              lat: coords[1],
              lng: coords[0],
              severity: isCritical ? 'high' : 'medium',
              location: 'India',
              detail: `Source: ${props.html || 'GDELT Monitor'}`
           });
        });
        statuses.gdelt = { status: 'live', updatedAt };
      } else {
        statuses.gdelt = { status: 'degraded', updatedAt };
      }

      if (ransomResult.status === 'fulfilled') {
         const data = Array.isArray(ransomResult.value) ? ransomResult.value : [];
         data.slice(0, 20).forEach((post: any) => {
             buckets.push({
                id: `ransom-${post.id || post.post_title}`,
                source: 'ransom',
                sourceLabel: SOURCE_META.ransom.label,
                title: `Ransomware Victim: ${post.post_title}`,
                time: formatUtc(post.date),
                lat: undefined,
                lng: undefined,
                severity: 'high',
                location: post.group_name ? `Group: ${post.group_name}` : 'Global',
                detail: `Victim listed on ${post.group_name} leak site.`,
                url: post.post_url
             });
         });
         statuses.ransom = { status: 'live', updatedAt };
      } else {
         statuses.ransom = { status: 'degraded', updatedAt };
      }

      if (newsResult.status === 'fulfilled') {
         const result = newsResult.value as any;
         if (result.status === 'success' && Array.isArray(result.articles)) {
            result.articles.forEach((item: any, idx: number) => {
               buckets.push({
                  id: `news-${idx}-${item.title.substring(0, 10)}`,
                  source: 'news',
                  sourceLabel: SOURCE_META.news.label,
                  title: item.title,
                  time: formatUtc(item.time),
                  lat: undefined, // Feed only
                  lng: undefined, // Feed only
                  severity: item.severity as Severity,
                  location: item.category, // e.g., "CIVIL UNREST"
                  detail: `Source: ${item.source}`,
                  url: item.url
               });
            });
            statuses.news = { status: 'live', updatedAt };
         } else {
            statuses.news = { status: 'degraded', updatedAt };
         }
      } else {
         statuses.news = { status: 'degraded', updatedAt };
      }

      const sorted = buckets.sort((a, b) => resolveTimeValue(b.time) - resolveTimeValue(a.time));
      setEvents(sorted);
      setSourceStatus(statuses);
      setLoading(false);
    };

    load();
    const interval = window.setInterval(load, REFRESH_MS);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, []);
  const filteredEvents = useMemo(() => {
    return events.filter(event => {
      if (!activeSources[event.source]) return false;
      if (severityRank[event.severity] < severityRank[minSeverity]) return false;
      if (search) {
        const haystack = `${event.title} ${event.location ?? ''} ${event.sourceLabel}`.toLowerCase();
        if (!haystack.includes(search.toLowerCase())) return false;
      }
      if (focusIndia && event.lat !== undefined && event.lng !== undefined) {
        const inIndia = event.lat >= 6 && event.lat <= 36 && event.lng >= 68 && event.lng <= 98;
        if (!inIndia) return false;
      }
      return true;
    });
  }, [events, activeSources, minSeverity, search, focusIndia]);

  const mapEvents = useMemo<MapEvent[]>(() => {
    return filteredEvents
      .filter(event => Number.isFinite(event.lat) && Number.isFinite(event.lng))
      .map(event => ({
        id: event.id,
        lat: event.lat as number,
        lng: event.lng as number,
        severity: event.severity,
        label: event.title,
        color: SOURCE_META[event.source].color,
        sourceLabel: event.sourceLabel,
        time: event.time,
        location: event.location,
        detail: event.detail,
        url: event.url,
      }));
  }, [filteredEvents]);

  const topEvents = useMemo(() => {
    return [...mapEvents]
      .sort((a, b) => {
        const sev = severityRank[b.severity] - severityRank[a.severity];
        if (sev !== 0) return sev;
        return resolveTimeValue(b.time) - resolveTimeValue(a.time);
      })
      .slice(0, 5);
  }, [mapEvents]);

  useEffect(() => {
    if (!autoRotate || selected || topEvents.length === 0) return;
    const timer = window.setInterval(() => {
      setSpotlightIndex((prev) => (prev + 1) % topEvents.length);
    }, 6000);
    return () => window.clearInterval(timer);
  }, [autoRotate, selected, topEvents.length]);

  const spotlightId = autoRotate && !selected ? topEvents[spotlightIndex]?.id : undefined;

  const liveSourceCount = useMemo(() => {
    return Object.values(sourceStatus).filter(item => item.status === 'live').length;
  }, [sourceStatus]);

  const statusText = `${liveSourceCount}/5 SOURCES LIVE • 60s REFRESH`;

  const sourcesList = (Object.keys(SOURCE_META) as SourceKey[]).map(key => ({
    key,
    ...SOURCE_META[key],
    status: sourceStatus[key]?.status ?? 'degraded',
  }));

  return (
    <div class="relative h-full w-full bg-black overflow-hidden font-mono">
      {/* 1. Full-Screen Map Layer */}
      <div class="absolute inset-0 z-0">
        <GlobalThreatMap
          events={mapEvents}
          loading={loading}
          statusText={statusText}
          scopeLabel={focusIndia ? 'INDIA' : 'GLOBAL'}
          selectedId={selected?.id ?? spotlightId}
          panelMode={panelMode}
          onPanelModeChange={setPanelMode}
          onClearSelection={() => setSelected(null)}
          onSelect={(event) => {
            const match = events.find(item => item.id === event.id);
            if (match) setSelected(match);
          }}
        />
      </div>

      {/* 2. Floating Control Dock (Top) */}
      <div class="absolute top-4 left-4 z-20 flex flex-col gap-2">
         {/* Main Toggle */}
         <div class="flex bg-black/80 backdrop-blur border border-neutral-700 rounded p-1 shadow-lg">
             <button
               onClick={() => setFocusIndia(true)}
               class={`px-4 py-1.5 text-xs font-bold uppercase tracking-wider ${focusIndia ? 'bg-primary-accent text-black' : 'text-gray-400 hover:text-white'}`}
             >
               India
             </button>
             <button
               onClick={() => setFocusIndia(false)}
               class={`px-4 py-1.5 text-xs font-bold uppercase tracking-wider ${!focusIndia ? 'bg-primary-accent text-black' : 'text-gray-400 hover:text-white'}`}
             >
               Global
             </button>
         </div>

         {/* New Briefings Button */}
         <a 
           href="/intelligence/briefings" 
           class="flex items-center gap-2 bg-neutral-900 border border-primary-accent/30 text-white px-4 py-2 rounded shadow-lg hover:bg-primary-accent hover:text-black transition-all group"
         >
            <span class="w-2 h-2 bg-primary-accent rounded-full animate-pulse group-hover:bg-black"></span>
            <span class="text-[10px] font-black uppercase tracking-widest">Strategic Briefings</span>
         </a>

         {/* Filter Toggles */}
         <div class="bg-black/80 backdrop-blur border border-neutral-700 rounded p-2 shadow-lg max-w-[200px]">
            <div class="text-[9px] text-gray-500 uppercase tracking-widest mb-2 font-bold">Signal Filters</div>
            <div class="flex flex-wrap gap-1.5">
               {sourcesList.map(source => (
                  <button
                    key={source.key}
                    onClick={() => setActiveSources(prev => ({ ...prev, [source.key]: !prev[source.key] }))}
                    class={`text-[10px] px-2 py-1 rounded border flex items-center gap-2 w-full ${activeSources[source.key] ? 'border-neutral-500 text-white bg-neutral-800' : 'border-neutral-800 text-gray-600'} transition-all`}
                  >
                    <span class="w-1.5 h-1.5 rounded-full" style={{ background: source.color }}></span>
                    {source.label}
                  </button>
               ))}
            </div>
         </div>
      </div>

      {/* 3. Floating Event Panel (Right Side) */}
      <div class={`absolute top-4 bottom-24 right-4 z-20 w-[380px] flex flex-col transition-transform duration-300 ${showEventsPanel ? 'translate-x-0' : 'translate-x-[400px]'}`}>
        
        {/* Panel Header */}
        <div class="bg-neutral-950/90 backdrop-blur border border-neutral-700 border-b-0 rounded-t p-3 flex justify-between items-center shadow-lg">
            <div class="flex items-center gap-2">
                <span class="w-2 h-2 bg-red-500 animate-pulse rounded-full"></span>
                <span class="text-xs font-bold text-white uppercase tracking-widest">Live Feed</span>
            </div>
            <div class="flex items-center gap-2">
                 <span class="text-[10px] text-gray-500 font-mono">{filteredEvents.length} EVENTS</span>
            </div>
        </div>

        {/* Panel Content */}
        <div class="flex-1 bg-black/80 backdrop-blur border border-neutral-700 overflow-y-auto scrollbar-thin scrollbar-thumb-neutral-700 scrollbar-track-transparent">
             <div class="sticky top-0 bg-neutral-900/90 border-b border-neutral-800 p-2 z-10">
                 <input
                   value={search}
                   onInput={(e) => setSearch((e.target as HTMLInputElement).value)}
                   placeholder="FILTER LOGS..."
                   class="w-full bg-black border border-neutral-700 text-xs text-white p-2 rounded focus:border-primary-accent focus:outline-none uppercase font-mono"
                 />
             </div>

             <div class="divide-y divide-neutral-800">
                {filteredEvents.map(event => (
                   <div
                     key={event.id}
                     onClick={() => setSelected(event)}
                     class={`p-3 hover:bg-white/5 cursor-pointer border-l-2 transition-colors ${selected?.id === event.id ? 'border-primary-accent bg-white/5' : 'border-transparent'}`}
                   >
                      <div class="flex justify-between items-start mb-1">
                          <span class="text-[9px] text-gray-500 font-mono">{displayTime(event.time)}</span>
                          <span class={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded ${event.severity === 'critical' ? 'bg-red-900/30 text-red-400' : event.severity === 'high' ? 'bg-orange-900/30 text-orange-400' : 'bg-neutral-800 text-gray-400'}`}>
                             {event.severity}
                          </span>
                      </div>
                      <h4 class="text-xs font-bold text-gray-200 mb-1 leading-snug">{event.title}</h4>
                      <div class="flex justify-between items-center">
                          <span class="text-[10px] text-primary-accent uppercase">{event.sourceLabel}</span>
                          <span class="text-[10px] text-gray-500 truncate max-w-[120px]">{event.location}</span>
                      </div>
                   </div>
                ))}
                {filteredEvents.length === 0 && (
                   <div class="p-8 text-center text-gray-500 text-xs font-mono">
                      NO SIGNALS DETECTED
                   </div>
                )}
             </div>
        </div>
      </div>
      
      {/* Toggle Panel Button */}
      <button
        onClick={() => setShowEventsPanel(!showEventsPanel)}
        class="absolute top-4 right-4 z-30 w-8 h-8 bg-black/80 border border-neutral-700 rounded flex items-center justify-center text-white hover:bg-neutral-800 transition-colors"
        style={{ right: showEventsPanel ? '400px' : '16px' }}
      >
        {showEventsPanel ? '»' : '«'}
      </button>

      {/* Selected Event Detail Overlay (Bottom Center) */}
      {selected && (
         <div class="absolute bottom-24 left-1/2 -translate-x-1/2 z-30 w-[600px] max-w-full bg-black/90 backdrop-blur border border-primary-accent/50 rounded-lg p-6 shadow-[0_0_30px_rgba(0,0,0,0.8)] animate-in fade-in slide-in-from-bottom-4 flex flex-col md:flex-row overflow-hidden">
             
             {/* Left: Event Info */}
             <div class="p-6 md:w-1/2 border-b md:border-b-0 md:border-r border-neutral-800">
                 <button
                   onClick={() => setSelected(null)}
                   class="absolute top-2 right-2 md:hidden text-gray-500 hover:text-white"
                 >
                   ×
                 </button>
                 <div class="flex items-center gap-3 mb-4">
                     <div class={`px-3 py-1 text-xs font-black uppercase tracking-widest rounded ${selected.severity === 'critical' ? 'bg-red-600 text-white' : 'bg-neutral-700 text-gray-300'}`}>
                        {selected.severity} ALERT
                     </div>
                     <div class="text-xs text-primary-accent font-mono uppercase">
                        SOURCE: {selected.sourceLabel}
                     </div>
                 </div>
                 <h2 class="text-xl font-bold text-white mb-2 leading-tight">{selected.title}</h2>
                 <p class="text-sm text-gray-400 leading-relaxed mb-4 border-l-2 border-neutral-700 pl-3">
                    {selected.detail || "No specific details available via public feed."}
                 </p>
                 <div class="text-[10px] text-gray-600 font-mono mt-auto">
                    ID: {selected.id}
                 </div>
             </div>

             {/* Right: ACTION PROTOCOL (The Utility Layer) */}
             <div class="p-6 md:w-1/2 bg-neutral-900/50">
                 <button
                   onClick={() => setSelected(null)}
                   class="hidden md:block absolute top-2 right-2 text-gray-500 hover:text-white"
                 >
                   ×
                 </button>
                 <div class="flex items-center gap-2 mb-4">
                     <span class="w-1.5 h-1.5 rounded-full bg-primary-accent animate-pulse"></span>
                     <h3 class="text-xs font-black text-white uppercase tracking-widest">SPS Recommended Protocol</h3>
                 </div>
                 
                 <ul class="space-y-3 mb-6">
                    {getProtocols(selected).map((step, idx) => (
                        <li key={idx} class="flex items-start gap-3 text-sm text-gray-300">
                            <span class="text-primary-accent font-mono font-bold mt-0.5">0{idx + 1}.</span>
                            <span class="leading-snug">{step}</span>
                        </li>
                    ))}
                 </ul>

                 <button class="w-full py-2 bg-white/5 border border-white/10 hover:bg-white/10 text-xs font-bold text-white uppercase tracking-widest transition-colors flex items-center justify-center gap-2 group">
                    <span>Generate PDF Report</span>
                    <span class="group-hover:translate-x-1 transition-transform">→</span>
                 </button>
             </div>
         </div>
      )}
    </div>
  );
}