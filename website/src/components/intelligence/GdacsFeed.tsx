import { useLiveFeed } from '../../hooks/useLiveFeed';

interface GdacsThreat {
  id: string;
  title: string;
  typeLabel: string;
  alertLevel: 'green' | 'yellow' | 'orange' | 'red' | 'unknown';
  country?: string;
  time?: string;
  lat: number;
  lng: number;
}

const GDACS_ENDPOINT = 'https://www.gdacs.org/gdacsapi/api/Events/geteventlist/EVENTS4APP';

const EVENT_TYPE_LABELS: Record<string, string> = {
  EQ: 'Earthquake',
  TC: 'Cyclone',
  FL: 'Flood',
  VO: 'Volcano',
  DR: 'Drought',
  WF: 'Wildfire',
  TS: 'Tsunami',
};

const normalizeAlert = (level?: string): GdacsThreat['alertLevel'] => {
  if (!level) return 'unknown';
  const cleaned = level.toLowerCase();
  if (cleaned.includes('red')) return 'red';
  if (cleaned.includes('orange')) return 'orange';
  if (cleaned.includes('yellow')) return 'yellow';
  if (cleaned.includes('green')) return 'green';
  return 'unknown';
};

const formatTime = (value?: string) => {
  if (!value) return undefined;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return new Date(parsed).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  });
};

const buildThreats = (data: any): GdacsThreat[] => {
  const features = Array.isArray(data?.features) ? data.features : [];
  return features
    .map((feature: any, index: number) => {
      const props = feature?.properties ?? {};
      const coords = feature?.geometry?.coordinates ?? [];
      const lng = Number(coords?.[0]);
      const lat = Number(coords?.[1]);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;

      const eventType = props.eventtype || props.eventType || props.type || 'EVENT';
      const typeLabel = EVENT_TYPE_LABELS[eventType] || String(eventType).toUpperCase();
      const alertLevel = normalizeAlert(props.alertlevel || props.alertLevel);
      const title = props.eventname || props.name || `${typeLabel} Alert`;

      return {
        id: String(props.eventid || props.eventId || `${eventType}-${index}`),
        title,
        typeLabel,
        alertLevel,
        country: props.country || props.countryname || props.countryName,
        time: formatTime(props.lastupdate || props.fromdate || props.date || props.datetime),
        lat,
        lng,
      } as GdacsThreat;
    })
    .filter(Boolean) as GdacsThreat[];
};

const getSearchable = (item: GdacsThreat) =>
  `${item.title} ${item.country ?? ''}`;

const badge = {
  red: 'bg-red-600/20 text-red-300 border-red-500/40',
  orange: 'bg-orange-600/20 text-orange-300 border-orange-500/40',
  yellow: 'bg-yellow-500/20 text-yellow-200 border-yellow-400/40',
  green: 'bg-emerald-600/20 text-emerald-300 border-emerald-500/40',
  unknown: 'bg-gray-700/40 text-gray-300 border-gray-600',
} as const;

export default function GdacsFeed() {
  const {
    visibleItems,
    pinnedItems,
    status,
    updatedAt,
    watchlist,
    showOnlyWatchlist,
    setWatchlist,
    setShowOnlyWatchlist,
    saveWatchlist,
  } = useLiveFeed<any, GdacsThreat>({
    endpoint: GDACS_ENDPOINT,
    cacheKey: 'sps-gdacs-feed',
    watchlistKey: 'sps-gdacs-watchlist',
    normalize: buildThreats,
    getSearchable,
  });

  const renderItem = (item: GdacsThreat, isPinned = false) => {
    const baseClass = isPinned
      ? 'bg-emerald-900/10 border border-emerald-700/40 p-3 rounded'
      : 'bg-neutral-900/50 border border-neutral-800 p-4 rounded';

    return (
      <div key={isPinned ? `pin-${item.id}` : item.id} class={baseClass}>
        <div class="flex items-center justify-between text-xs text-gray-400 mb-1">
          <span class={`px-2 py-0.5 rounded border ${badge[item.alertLevel]}`}>
            {item.alertLevel.toUpperCase()}
          </span>
          <span class="font-mono">{item.time || '—'}</span>
        </div>
        <div class="text-white font-bold">{item.typeLabel}</div>
        <p class="text-sm text-gray-400">
          {item.title}{item.country ? ` • ${item.country}` : ''}
        </p>
      </div>
    );
  };

  return (
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-white font-bold text-sm">Physical Threats</h3>
        <span class={`text-[10px] font-mono px-2 py-0.5 rounded border ${status === 'live' ? 'border-emerald-500/50 text-emerald-400' : status === 'loading' ? 'border-yellow-500/50 text-yellow-400' : 'border-red-500/50 text-red-400'}`}>
          {status === 'loading' ? 'SYNCING' : status === 'live' ? 'LIVE' : 'DEGRADED'}
        </span>
      </div>
      <p class="text-xs text-gray-500">UN/EU GDACS alerts with live coordinates.</p>
      <form
        class="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          saveWatchlist();
        }}
      >
        <input
          type="text"
          value={watchlist}
          onInput={(event) => setWatchlist((event.target as HTMLInputElement).value)}
          placeholder="Watchlist: India, Mumbai, Gujarat"
          class="w-full bg-black border border-neutral-700 text-white p-2 text-xs rounded focus:border-emerald-500 focus:outline-none"
        />
        <div class="flex items-center justify-between text-[10px] text-gray-500">
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              checked={showOnlyWatchlist}
              onChange={(event) => setShowOnlyWatchlist((event.target as HTMLInputElement).checked)}
              class="accent-emerald-400"
            />
            Show watchlist only
          </label>
          <button type="submit" class="text-emerald-300 hover:text-emerald-200 font-mono uppercase tracking-widest">
            Save Watchlist
          </button>
        </div>
      </form>
      {pinnedItems.length > 0 && (
        <div class="space-y-2">
          <div class="text-[10px] uppercase tracking-widest text-emerald-300">Pinned Alerts</div>
          {pinnedItems.slice(0, 3).map(item => renderItem(item, true))}
        </div>
      )}
      <div class="space-y-3">
        {visibleItems.length === 0 && status !== 'loading' && (
          <div class="text-sm text-gray-500">No events returned. Stand by.</div>
        )}
        {visibleItems.map(item => renderItem(item))}
      </div>
      <p class="text-[10px] text-gray-600">Last sync: {updatedAt || '—'} UTC</p>
    </div>
  );
}
