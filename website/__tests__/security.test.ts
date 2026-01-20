import { describe, it, expect, vi } from 'vitest';

/**
 * Tests for Security Utilities
 *
 * These tests verify:
 * 1. CSRF protection via origin validation
 * 2. Fetch timeout functionality
 */

describe('validateOrigin (CSRF Protection)', () => {
  it('should accept requests from allowed origins', async () => {
    const { validateOrigin } = await import('../src/utils/security');

    const allowedOrigins = ['https://sps-security.com', 'http://localhost:4321'];
    const result = validateOrigin('https://sps-security.com', allowedOrigins);

    expect(result).toBe(true);
  });

  it('should accept localhost during development', async () => {
    const { validateOrigin } = await import('../src/utils/security');

    const allowedOrigins = ['https://sps-security.com', 'http://localhost:4321'];
    const result = validateOrigin('http://localhost:4321', allowedOrigins);

    expect(result).toBe(true);
  });

  it('should reject requests from disallowed origins', async () => {
    const { validateOrigin } = await import('../src/utils/security');

    const allowedOrigins = ['https://sps-security.com'];
    const result = validateOrigin('https://evil.com', allowedOrigins);

    expect(result).toBe(false);
  });

  it('should reject requests with null origin', async () => {
    const { validateOrigin } = await import('../src/utils/security');

    const allowedOrigins = ['https://sps-security.com'];
    const result = validateOrigin(null, allowedOrigins);

    expect(result).toBe(false);
  });

  it('should reject requests with undefined origin', async () => {
    const { validateOrigin } = await import('../src/utils/security');

    const allowedOrigins = ['https://sps-security.com'];
    const result = validateOrigin(undefined, allowedOrigins);

    expect(result).toBe(false);
  });
});

describe('fetchWithTimeout', () => {
  it('should complete fetch before timeout', async () => {
    const { fetchWithTimeout } = await import('../src/utils/security');

    // Mock a fast response
    const mockFetch = vi.fn().mockResolvedValue(new Response('ok'));
    global.fetch = mockFetch;

    const result = await fetchWithTimeout('https://example.com', {}, 5000);
    expect(result.ok).toBe(true);
  });

  it('should abort fetch after timeout', async () => {
    const { fetchWithTimeout } = await import('../src/utils/security');

    // Mock a fetch that respects AbortSignal
    const mockFetch = vi.fn().mockImplementation((_url, options) => {
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => resolve(new Response('ok')), 10000);
        options?.signal?.addEventListener('abort', () => {
          clearTimeout(timer);
          reject(new DOMException('Aborted', 'AbortError'));
        });
      });
    });
    global.fetch = mockFetch;

    await expect(fetchWithTimeout('https://example.com', {}, 50)).rejects.toThrow();
  }, 1000);

  it('should pass signal to fetch options', async () => {
    const { fetchWithTimeout } = await import('../src/utils/security');

    const mockFetch = vi.fn().mockResolvedValue(new Response('ok'));
    global.fetch = mockFetch;

    await fetchWithTimeout('https://example.com', { method: 'POST' }, 5000);

    expect(mockFetch).toHaveBeenCalledWith(
      'https://example.com',
      expect.objectContaining({
        method: 'POST',
        signal: expect.any(AbortSignal),
      })
    );
  });
});

describe('createCsrfResponse', () => {
  it('should create a 403 Forbidden response', async () => {
    const { createCsrfResponse } = await import('../src/utils/security');

    const response = createCsrfResponse();

    expect(response.status).toBe(403);
    const body = await response.json();
    expect(body.error).toBe('Forbidden');
  });
});
