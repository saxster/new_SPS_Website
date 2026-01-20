import type { APIRoute } from 'astro';
import { validateOrigin, DEFAULT_ALLOWED_ORIGINS } from '../../utils/security';

// Server-rendered API route for proxying external intelligence feeds
export const prerender = false;

// External API endpoints
const ENDPOINTS: Record<string, string> = {
  gdacs: 'https://www.gdacs.org/gdacsapi/api/Events/geteventlist/EVENTS4APP',
  usgs: 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson',
  eonet: 'https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=50',
  swpc: 'https://services.swpc.noaa.gov/products/alerts.json',
};

// Default Indian cities for AQI data
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

// Rate limiting (in-memory)
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 30; // 30 requests per minute
const RATE_WINDOW_MS = 60 * 1000;

const checkRateLimit = (ip: string): boolean => {
  const now = Date.now();
  const record = rateLimitMap.get(ip);

  if (!record || now > record.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS });
    return true;
  }

  if (record.count >= RATE_LIMIT) {
    return false;
  }

  record.count++;
  return true;
};

// Build AQI endpoint URL
const buildAqiUrl = (): string => {
  const latitudes = INDIA_AQI_LOCATIONS.map(city => city.lat).join(',');
  const longitudes = INDIA_AQI_LOCATIONS.map(city => city.lng).join(',');
  return `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${latitudes}&longitude=${longitudes}&hourly=us_aqi,pm2_5&timezone=UTC`;
};

export const GET: APIRoute = async ({ request, url, clientAddress }) => {
  const source = url.searchParams.get('source');

  const origin = request.headers.get('origin');
  const allowedOrigin = validateOrigin(origin, DEFAULT_ALLOWED_ORIGINS) ? origin : 'null';
  const corsHeaders = {
    'Access-Control-Allow-Origin': allowedOrigin || 'null',
    'Vary': 'Origin',
  };

  if (!source) {
    return new Response(
      JSON.stringify({ error: 'Missing required parameter: source' }),
      { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    );
  }

  // Rate limiting
  const ip = clientAddress || 'unknown';
  if (!checkRateLimit(ip)) {
    return new Response(
      JSON.stringify({ error: 'Too many requests. Please try again later.' }),
      { status: 429, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    );
  }

  // Determine the target URL
  let targetUrl: string;

  if (source === 'aqi') {
    targetUrl = buildAqiUrl();
  } else if (ENDPOINTS[source]) {
    targetUrl = ENDPOINTS[source];
  } else {
    return new Response(
      JSON.stringify({ error: `Unknown source: ${source}` }),
      { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    );
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout

    const response = await fetch(targetUrl, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'SPS-Intelligence-Dashboard/1.0',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return new Response(
        JSON.stringify({
          error: `Upstream API error: ${response.status} ${response.statusText}`,
        }),
        { status: 502, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    const data = await response.json();

    return new Response(JSON.stringify(data), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=60', // Cache for 60 seconds
        ...corsHeaders,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';

    if (message.includes('abort')) {
      return new Response(
        JSON.stringify({ error: 'Request timed out' }),
        { status: 504, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    console.error(`[Intel Proxy] Error fetching ${source}:`, message);

    return new Response(
      JSON.stringify({ error: `Failed to fetch data: ${message}` }),
      { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    );
  }
};

// Handle OPTIONS for CORS preflight
export const OPTIONS: APIRoute = async ({ request }) => {
  const origin = request.headers.get('origin');
  const allowedOrigin = validateOrigin(origin, DEFAULT_ALLOWED_ORIGINS) ? origin : 'null';

  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': allowedOrigin || 'null',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400',
      'Vary': 'Origin',
    },
  });
};
