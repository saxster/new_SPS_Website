import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

/**
 * Tests for SSE Streaming in Ask Expert API
 *
 * These tests verify:
 * 1. GET endpoint returns SSE content-type headers
 * 2. GET endpoint requires query parameter
 * 3. GET endpoint streams tokens in SSE format
 * 4. Rate limiting applies to streaming endpoint
 * 5. Cached responses are returned immediately
 */

// Store original fetch
const originalFetch = global.fetch;

describe('Ask Expert SSE Streaming API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('GET endpoint', () => {
    it('should return SSE content-type headers', async () => {
      // This test should fail until we implement the GET endpoint
      const { GET } = await import('../src/pages/api/ask-expert');

      expect(GET).toBeDefined();

      const mockRequest = new Request('http://localhost/api/ask-expert?query=test', {
        method: 'GET',
        headers: {
          'origin': 'http://localhost:4321',
        },
      });

      const response = await GET({
        request: mockRequest,
        clientAddress: '127.0.0.1'
      } as any);

      expect(response.headers.get('Content-Type')).toBe('text/event-stream');
      expect(response.headers.get('Cache-Control')).toBe('no-cache');
      expect(response.headers.get('Connection')).toBe('keep-alive');
    });

    it('should require query parameter', async () => {
      const { GET } = await import('../src/pages/api/ask-expert');

      const mockRequest = new Request('http://localhost/api/ask-expert', {
        method: 'GET',
        headers: {
          'origin': 'http://localhost:4321',
        },
      });

      const response = await GET({
        request: mockRequest,
        clientAddress: '127.0.0.1'
      } as any);

      expect(response.status).toBe(400);
      const data = await response.json();
      expect(data.error).toBe('Query is required.');
    });

    it('should reject queries over 1000 characters', async () => {
      const { GET } = await import('../src/pages/api/ask-expert');

      const longQuery = 'a'.repeat(1001);
      const mockRequest = new Request(`http://localhost/api/ask-expert?query=${encodeURIComponent(longQuery)}`, {
        method: 'GET',
        headers: {
          'origin': 'http://localhost:4321',
        },
      });

      const response = await GET({
        request: mockRequest,
        clientAddress: '127.0.0.1'
      } as any);

      expect(response.status).toBe(400);
      const data = await response.json();
      expect(data.error).toBe('Query too long. Maximum 1000 characters.');
    });

    it('should apply rate limiting', async () => {
      const { GET } = await import('../src/pages/api/ask-expert');

      // Make 11 requests (limit is 10)
      for (let i = 0; i < 11; i++) {
        const mockRequest = new Request(`http://localhost/api/ask-expert?query=test${i}`, {
          method: 'GET',
          headers: {
            'origin': 'http://localhost:4321',
          },
        });

        const response = await GET({
          request: mockRequest,
          clientAddress: '192.168.1.1' // Same IP for all requests
        } as any);

        if (i < 10) {
          expect(response.status).not.toBe(429);
        } else {
          expect(response.status).toBe(429);
          const data = await response.json();
          expect(data.error).toContain('Rate limit exceeded');
        }
      }
    });
  });

  describe('SSE Format', () => {
    it('should return response in SSE format with data prefix', async () => {
      const { GET } = await import('../src/pages/api/ask-expert');

      const mockRequest = new Request('http://localhost/api/ask-expert?query=test', {
        method: 'GET',
        headers: {
          'origin': 'http://localhost:4321',
        },
      });

      const response = await GET({
        request: mockRequest,
        clientAddress: '127.0.0.2'
      } as any);

      expect(response.body).toBeInstanceOf(ReadableStream);

      // Read the stream
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let result = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        result += decoder.decode(value);
      }

      // Verify SSE format: each message should be "data: {...}\n\n"
      expect(result).toContain('data:');
      // Fallback response returns full response in one event
      expect(result).toContain('"response"');
    });

    it('should send done event when streaming completes', async () => {
      const { GET } = await import('../src/pages/api/ask-expert');

      const mockRequest = new Request('http://localhost/api/ask-expert?query=complete', {
        method: 'GET',
        headers: {
          'origin': 'http://localhost:4321',
        },
      });

      const response = await GET({
        request: mockRequest,
        clientAddress: '127.0.0.3'
      } as any);

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let result = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        result += decoder.decode(value);
      }

      expect(result).toContain('"done":true');
    });

    it('should return fallback response when no API keys configured', async () => {
      const { GET } = await import('../src/pages/api/ask-expert');

      const mockRequest = new Request('http://localhost/api/ask-expert?query=compliance+question', {
        method: 'GET',
        headers: {
          'origin': 'http://localhost:4321',
        },
      });

      const response = await GET({
        request: mockRequest,
        clientAddress: '127.0.0.6'
      } as any);

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let result = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        result += decoder.decode(value);
      }

      // Should contain compliance-specific fallback response
      expect(result).toContain('compliance');
      expect(result).toContain('"done":true');
    });
  });

  describe('Error Handling', () => {
    it('should return valid SSE response even without API keys', async () => {
      const { GET } = await import('../src/pages/api/ask-expert');

      const mockRequest = new Request('http://localhost/api/ask-expert?query=error-test', {
        method: 'GET',
        headers: {
          'origin': 'http://localhost:4321',
        },
      });

      const response = await GET({
        request: mockRequest,
        clientAddress: '127.0.0.4'
      } as any);

      // Should return 200 with SSE headers
      expect(response.status).toBe(200);
      expect(response.headers.get('Content-Type')).toBe('text/event-stream');

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let result = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        result += decoder.decode(value);
      }

      // Should return fallback response with done flag
      expect(result).toContain('"done":true');
      expect(result).toContain('"response"');
    });
  });

  describe('CSRF Protection', () => {
    it('should reject requests without valid origin', async () => {
      const { GET } = await import('../src/pages/api/ask-expert');

      const mockRequest = new Request('http://localhost/api/ask-expert?query=test', {
        method: 'GET',
        headers: {
          'origin': 'http://evil-site.com',
        },
      });

      const response = await GET({
        request: mockRequest,
        clientAddress: '127.0.0.5'
      } as any);

      expect(response.status).toBe(403);
    });
  });
});
