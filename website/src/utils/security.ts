/**
 * Security utilities for API endpoints
 *
 * Provides:
 * - CSRF protection via origin validation
 * - Fetch with timeout for external API calls
 */

/**
 * Validates that the request origin is in the allowed list.
 * Used for CSRF protection on API endpoints.
 *
 * @param origin - The origin header from the request (can be null/undefined)
 * @param allowedOrigins - List of allowed origin URLs
 * @returns true if origin is valid, false otherwise
 */
export function validateOrigin(
  origin: string | null | undefined,
  allowedOrigins: string[]
): boolean {
  if (!origin) {
    return false;
  }
  return allowedOrigins.includes(origin);
}

/**
 * Creates a standardized 403 Forbidden response for CSRF violations.
 *
 * @returns Response with 403 status and JSON error body
 */
export function createCsrfResponse(): Response {
  return new Response(JSON.stringify({ error: 'Forbidden' }), {
    status: 403,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Fetches a URL with a timeout to prevent hanging requests.
 *
 * @param url - The URL to fetch
 * @param options - Fetch options (method, headers, body, etc.)
 * @param timeoutMs - Timeout in milliseconds (default: 30000)
 * @returns Promise that resolves with Response or rejects on timeout
 */
export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = 30000
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Default allowed origins for the SPS website.
 * Includes production domain and localhost for development.
 */
const isProd = process.env.NODE_ENV === 'production';

export const DEFAULT_ALLOWED_ORIGINS = isProd
  ? ['https://sps-security.com']
  : ['https://sps-security.com', 'http://localhost:4321', 'http://localhost:3000'];
