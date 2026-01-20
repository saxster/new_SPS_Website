import { useLiveFeed } from '../../hooks/useLiveFeed';

interface CisaItem {
  id: string;
  title: string;
  cve?: string;
  vendor?: string;
  product?: string;
  dateAdded?: string;
  ransomware?: string;
}

const KEV_JSON = 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json';

const formatDate = (value?: string) => {
  if (!value) return '—';
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return new Date(parsed).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

const tagMap: Record<string, string> = {
  microsoft: 'Enterprise',
  cisco: 'Network',
  vmware: 'Virtualization',
  fortinet: 'Network Edge',
  palo: 'Network Edge',
  citrix: 'Access Gateway',
  apple: 'Endpoint',
  google: 'Cloud',
  ibm: 'Enterprise',
  oracle: 'Enterprise',
  juniper: 'Network',
  adobe: 'Productivity',
};

const detectImpactTag = (title: string) => {
  const lowered = title.toLowerCase();
  if (lowered.includes('remote code execution') || lowered.includes('rce')) return 'RCE';
  if (lowered.includes('privilege escalation')) return 'PrivEsc';
  if (lowered.includes('auth bypass') || lowered.includes('authentication bypass')) return 'Auth Bypass';
  if (lowered.includes('sql injection')) return 'SQLi';
  if (lowered.includes('command injection')) return 'Cmd Inject';
  if (lowered.includes('deserialization')) return 'Deserialization';
  return '';
};

const detectSectorTag = (vendor?: string) => {
  if (!vendor) return '';
  const lowered = vendor.toLowerCase();
  const key = Object.keys(tagMap).find(tag => lowered.includes(tag));
  return key ? tagMap[key] : '';
};

const isRecent = (date?: string) => {
  if (!date) return false;
  const parsed = Date.parse(date);
  if (Number.isNaN(parsed)) return false;
  return Date.now() - parsed < 1000 * 60 * 60 * 24 * 14;
};

const normalizeKev = (data: any): CisaItem[] => {
  const entries = Array.isArray(data?.vulnerabilities) ? data.vulnerabilities : [];
  return entries
    .map((entry: any, index: number) => ({
      id: entry.cveID || `kev-${index}`,
      title: entry.vulnerabilityName || `${entry.vendorProject || 'Unknown'} ${entry.product || ''}`.trim(),
      cve: entry.cveID,
      vendor: entry.vendorProject,
      product: entry.product,
      dateAdded: entry.dateAdded,
      ransomware: entry.knownRansomwareCampaignUse,
    }))
    .sort((a: CisaItem, b: CisaItem) => Date.parse(b.dateAdded || '') - Date.parse(a.dateAdded || ''));
};

const getSearchable = (item: CisaItem) =>
  `${item.title} ${item.vendor ?? ''} ${item.product ?? ''}`;

export default function CisaKevFeed() {
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
  } = useLiveFeed<any, CisaItem>({
    endpoint: KEV_JSON,
    cacheKey: 'sps-cisa-feed',
    watchlistKey: 'sps-cisa-watchlist',
    normalize: normalizeKev,
    getSearchable,
  });

  const renderItem = (item: CisaItem, isPinned = false) => {
    const impact = detectImpactTag(item.title);
    const sector = detectSectorTag(item.vendor);
    const baseClass = isPinned
      ? 'bg-blue-900/10 border border-blue-800/40 p-3 rounded'
      : 'bg-neutral-900/50 border border-neutral-800 p-4 rounded';

    return (
      <div key={isPinned ? `pin-${item.id}` : item.id} class={baseClass}>
        <div class="flex items-center justify-between text-xs text-gray-400 mb-1">
          <span class="font-mono text-blue-300">{item.cve || 'KEV'}</span>
          <span>{formatDate(item.dateAdded)}</span>
        </div>
        <div class="text-white font-bold">{item.title}</div>
        <p class="text-sm text-gray-400">
          {item.vendor ? `${item.vendor}${item.product ? ` • ${item.product}` : ''}` : 'CISA Known Exploited'}
        </p>
        <div class="flex flex-wrap gap-2 mt-2 text-[10px] uppercase tracking-widest text-gray-300">
          {item.ransomware && (
            <span class={`px-2 py-0.5 rounded border ${item.ransomware === 'Known' || item.ransomware === 'Yes' ? 'border-red-500/40 text-red-300' : 'border-gray-600 text-gray-400'}`}>
              Ransomware
            </span>
          )}
          {isRecent(item.dateAdded) && (
            <span class="px-2 py-0.5 rounded border border-emerald-500/40 text-emerald-300">New</span>
          )}
          {impact && <span class="px-2 py-0.5 rounded border border-yellow-500/40 text-yellow-300">{impact}</span>}
          {sector && <span class="px-2 py-0.5 rounded border border-blue-500/40 text-blue-200">{sector}</span>}
        </div>
      </div>
    );
  };

  return (
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-white font-bold text-sm">Cyber Threats</h3>
        <span class={`text-[10px] font-mono px-2 py-0.5 rounded border ${status === 'live' ? 'border-emerald-500/50 text-emerald-400' : status === 'loading' ? 'border-yellow-500/50 text-yellow-400' : 'border-red-500/50 text-red-400'}`}>
          {status === 'loading' ? 'SYNCING' : status === 'live' ? 'LIVE' : 'DEGRADED'}
        </span>
      </div>
      <p class="text-xs text-gray-500">CISA KEV: actively exploited vulnerabilities.</p>
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
          placeholder="Watchlist: Microsoft, Cisco, VMware"
          class="w-full bg-black border border-neutral-700 text-white p-2 text-xs rounded focus:border-blue-500 focus:outline-none"
        />
        <div class="flex items-center justify-between text-[10px] text-gray-500">
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              checked={showOnlyWatchlist}
              onChange={(event) => setShowOnlyWatchlist((event.target as HTMLInputElement).checked)}
              class="accent-blue-400"
            />
            Show watchlist only
          </label>
          <button type="submit" class="text-blue-300 hover:text-blue-200 font-mono uppercase tracking-widest">
            Save Watchlist
          </button>
        </div>
      </form>
      {pinnedItems.length > 0 && (
        <div class="space-y-2">
          <div class="text-[10px] uppercase tracking-widest text-blue-300">Pinned Threats</div>
          {pinnedItems.slice(0, 3).map(item => renderItem(item, true))}
        </div>
      )}
      <div class="space-y-3">
        {visibleItems.length === 0 && status !== 'loading' && (
          <div class="text-sm text-gray-500">No vulnerabilities returned. Stand by.</div>
        )}
        {visibleItems.map(item => renderItem(item))}
      </div>
      <p class="text-[10px] text-gray-600">Last sync: {updatedAt || '—'} UTC</p>
    </div>
  );
}
