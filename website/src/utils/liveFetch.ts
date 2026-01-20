export const fetchJsonWithCache = async <T>(
  url: string,
  cacheKey: string,
  ttlMs: number,
  options?: RequestInit
): Promise<T> => {
  if (typeof window !== 'undefined') {
    try {
      const cached = window.sessionStorage.getItem(cacheKey);
      if (cached) {
        const parsed = JSON.parse(cached) as { timestamp: number; payload: T };
        if (Date.now() - parsed.timestamp < ttlMs) {
          return parsed.payload;
        }
      }
    } catch {
      // Ignore cache read errors and fall through to network.
    }
  }

  const res = await fetch(url, { ...options, cache: 'no-store' });
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  const payload = (await res.json()) as T;

  if (typeof window !== 'undefined') {
    try {
      window.sessionStorage.setItem(cacheKey, JSON.stringify({ timestamp: Date.now(), payload }));
    } catch {
      // Ignore cache write errors.
    }
  }

  return payload;
};
