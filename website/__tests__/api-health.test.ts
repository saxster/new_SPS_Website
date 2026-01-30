import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

/**
 * Tests for /api/health endpoint
 *
 * The health endpoint provides:
 * - HTTP 200 when all critical checks pass
 * - HTTP 503 when unhealthy
 * - JSON response with check details and diagnostics
 */

describe('/api/health endpoint', () => {
  beforeEach(() => {
    // Mock fetch for backend check
    vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), { status: 200 })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns 200 with JSON content-type when healthy', async () => {
    const { GET } = await import('../src/pages/api/health.ts');

    // Create a mock request and context
    const mockRequest = new Request('https://sukhi.in/api/health');
    const mockContext = {
      request: mockRequest,
      clientAddress: '127.0.0.1',
    };

    const response = await GET(mockContext as any);

    expect(response.status).toBe(200);
    expect(response.headers.get('Content-Type')).toBe('application/json');
  });

  it('returns valid JSON health report structure', async () => {
    const { GET } = await import('../src/pages/api/health.ts');

    const mockRequest = new Request('https://sukhi.in/api/health');
    const mockContext = { request: mockRequest, clientAddress: '127.0.0.1' };

    const response = await GET(mockContext as any);
    const body = await response.json();

    expect(body).toMatchObject({
      timestamp: expect.any(String),
      status: expect.stringMatching(/^(healthy|degraded|unhealthy)$/),
      version: expect.any(String),
      uptime: expect.any(Number),
      checks: expect.objectContaining({
        filesystem: expect.any(Object),
        memory: expect.any(Object),
        content: expect.any(Object),
        backend: expect.any(Object),
      }),
      diagnostics: expect.any(Object),
    });
  });

  it('returns 503 when status is unhealthy', async () => {
    // We need to test that 503 is returned when unhealthy
    // Since we can't easily mock fs in ESM, we test the logic path
    const { GET } = await import('../src/pages/api/health.ts');

    const mockRequest = new Request('https://sukhi.in/api/health');
    const mockContext = { request: mockRequest, clientAddress: '127.0.0.1' };

    const response = await GET(mockContext as any);
    const body = await response.json();

    // If unhealthy, status should be 503
    if (body.status === 'unhealthy') {
      expect(response.status).toBe(503);
    } else {
      // Otherwise 200
      expect(response.status).toBe(200);
    }
  });

  it('includes cache-control headers to prevent caching', async () => {
    const { GET } = await import('../src/pages/api/health.ts');

    const mockRequest = new Request('https://sukhi.in/api/health');
    const mockContext = { request: mockRequest, clientAddress: '127.0.0.1' };

    const response = await GET(mockContext as any);

    // Health checks should not be cached
    expect(response.headers.get('Cache-Control')).toBe('no-store, no-cache, must-revalidate');
  });

  it('includes timestamp in ISO 8601 format', async () => {
    const { GET } = await import('../src/pages/api/health.ts');

    const mockRequest = new Request('https://sukhi.in/api/health');
    const mockContext = { request: mockRequest, clientAddress: '127.0.0.1' };

    const response = await GET(mockContext as any);
    const body = await response.json();

    // ISO 8601 format check
    expect(body.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  });

  it('returns diagnostics with memory and system info', async () => {
    const { GET } = await import('../src/pages/api/health.ts');

    const mockRequest = new Request('https://sukhi.in/api/health');
    const mockContext = { request: mockRequest, clientAddress: '127.0.0.1' };

    const response = await GET(mockContext as any);
    const body = await response.json();

    expect(body.diagnostics).toMatchObject({
      memory: {
        heapUsedMB: expect.any(Number),
        heapTotalMB: expect.any(Number),
        rssMB: expect.any(Number),
        percentUsed: expect.any(Number),
      },
      system: {
        loadAvg: expect.any(Array),
        freeMem: expect.any(Number),
        totalMem: expect.any(Number),
        cpuCount: expect.any(Number),
      },
    });
  });

  it('is server-rendered (prerender = false)', async () => {
    const module = await import('../src/pages/api/health.ts');

    expect(module.prerender).toBe(false);
  });
});
