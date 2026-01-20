import { useEffect, useMemo, useState } from 'preact/hooks';
import { fetchJsonWithCache } from '../utils/liveFetch';

export type FeedStatus = 'idle' | 'loading' | 'live' | 'degraded';

export interface UseLiveFeedOptions<TRaw, TItem extends { id: string }> {
  /** API endpoint URL */
  endpoint: string;
  /** Cache key for localStorage */
  cacheKey: string;
  /** Watchlist localStorage key */
  watchlistKey: string;
  /** Cache TTL in milliseconds */
  cacheTtlMs?: number;
  /** Refresh interval in milliseconds */
  refreshMs?: number;
  /** Maximum items to display */
  maxItems?: number;
  /** Transform raw API data to normalized items */
  normalize: (data: TRaw) => TItem[];
  /** Build search haystack from item for watchlist matching */
  getSearchable: (item: TItem) => string;
}

export interface UseLiveFeedResult<TItem> {
  /** All fetched items */
  items: TItem[];
  /** Items visible based on watchlist filter */
  visibleItems: TItem[];
  /** Items matching watchlist terms */
  pinnedItems: TItem[];
  /** Current feed status */
  status: FeedStatus;
  /** Last update timestamp string */
  updatedAt: string;
  /** Current watchlist input value */
  watchlist: string;
  /** Parsed watchlist terms */
  watchTerms: string[];
  /** Whether to show only watchlist items */
  showOnlyWatchlist: boolean;
  /** Update watchlist input */
  setWatchlist: (value: string) => void;
  /** Toggle show only watchlist */
  setShowOnlyWatchlist: (value: boolean) => void;
  /** Save watchlist to localStorage */
  saveWatchlist: () => void;
}

const DEFAULT_CACHE_TTL = 60000;
const DEFAULT_REFRESH_MS = 60000;
const DEFAULT_MAX_ITEMS = 8;

/**
 * Reusable hook for live intelligence feeds with caching, watchlist, and auto-refresh.
 */
export function useLiveFeed<TRaw, TItem extends { id: string }>(
  options: UseLiveFeedOptions<TRaw, TItem>
): UseLiveFeedResult<TItem> {
  const {
    endpoint,
    cacheKey,
    watchlistKey,
    cacheTtlMs = DEFAULT_CACHE_TTL,
    refreshMs = DEFAULT_REFRESH_MS,
    maxItems = DEFAULT_MAX_ITEMS,
    normalize,
    getSearchable,
  } = options;

  const [items, setItems] = useState<TItem[]>([]);
  const [status, setStatus] = useState<FeedStatus>('loading');
  const [updatedAt, setUpdatedAt] = useState<string>('');
  const [watchlist, setWatchlist] = useState<string>('');
  const [showOnlyWatchlist, setShowOnlyWatchlist] = useState(false);

  // Fetch and refresh data
  useEffect(() => {
    const controller = new AbortController();

    const load = async () => {
      try {
        setStatus('loading');
        const data = await fetchJsonWithCache<TRaw>(endpoint, cacheKey, cacheTtlMs, {
          signal: controller.signal,
        });
        const normalized = normalize(data);
        setItems(normalized.slice(0, maxItems));
        setUpdatedAt(
          new Date().toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short',
          })
        );
        setStatus('live');
      } catch (error) {
        if ((error as Error).name === 'AbortError') return;
        setStatus('degraded');
      }
    };

    load();
    const interval = window.setInterval(load, refreshMs);

    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, [endpoint, cacheKey, cacheTtlMs, refreshMs, maxItems, normalize]);

  // Load watchlist from localStorage
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(watchlistKey);
      if (saved) setWatchlist(saved);
    } catch {
      // Ignore storage issues
    }
  }, [watchlistKey]);

  // Parse watchlist terms
  const watchTerms = useMemo(
    () =>
      watchlist
        .split(',')
        .map((term) => term.trim().toLowerCase())
        .filter(Boolean),
    [watchlist]
  );

  // Filter pinned items matching watchlist
  const pinnedItems = useMemo(() => {
    if (watchTerms.length === 0) return [];
    return items.filter((item) => {
      const haystack = getSearchable(item).toLowerCase();
      return watchTerms.some((term) => haystack.includes(term));
    });
  }, [items, watchTerms, getSearchable]);

  // Determine visible items based on filter
  const visibleItems = showOnlyWatchlist && watchTerms.length > 0 ? pinnedItems : items;

  // Save watchlist to localStorage
  const saveWatchlist = () => {
    try {
      window.localStorage.setItem(watchlistKey, watchlist);
    } catch {
      // Ignore storage issues
    }
  };

  return {
    items,
    visibleItems,
    pinnedItems,
    status,
    updatedAt,
    watchlist,
    watchTerms,
    showOnlyWatchlist,
    setWatchlist,
    setShowOnlyWatchlist,
    saveWatchlist,
  };
}
