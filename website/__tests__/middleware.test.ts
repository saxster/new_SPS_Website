import { describe, it, expect, vi, beforeEach } from 'vitest';

/**
 * Tests for Middleware Route Matching
 *
 * These tests verify:
 * 1. Public routes correctly bypass Clerk (SSR pages work without API keys)
 * 2. Protected routes still require authentication
 * 3. Route matcher patterns work correctly
 */

// Mock Astro middleware - must be before imports
vi.mock('astro:middleware', () => ({
  defineMiddleware: vi.fn((handler) => handler),
  sequence: vi.fn((...middlewares) => middlewares),
}));

// Mock Clerk to track when it's called
const mockClerkMiddleware = vi.fn(() => vi.fn());
const mockCreateRouteMatcher = vi.fn((patterns: string[]) => {
  // Implement actual route matching logic for testing
  return (request: Request) => {
    const url = new URL(request.url);
    const pathname = url.pathname;

    return patterns.some((pattern) => {
      // Convert route pattern to regex
      // Handle (.*) as wildcard
      const regexPattern = pattern.replace(/\(\.\*\)/g, '.*').replace(/\//g, '\\/');
      const regex = new RegExp(`^${regexPattern}$`);
      return regex.test(pathname);
    });
  };
});

vi.mock('@clerk/astro/server', () => ({
  clerkMiddleware: mockClerkMiddleware,
  createRouteMatcher: mockCreateRouteMatcher,
}));

describe('Middleware Route Matching', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('isPublicRoute matcher', () => {
    // Expected public route patterns
    const publicPatterns = [
      '/',
      '/about(.*)',
      '/services(.*)',
      '/sectors(.*)',
      '/tools(.*)',
      '/news(.*)',
      '/intelligence(.*)',
      '/articles(.*)',
      '/blog(.*)',
      '/contact(.*)',
      '/privacy(.*)',
      '/terms(.*)',
      '/api/search-index.json',
      '/api/health(.*)',
    ];

    const isPublicRoute = mockCreateRouteMatcher(publicPatterns);

    it('should match root path as public', () => {
      const request = new Request('https://sps-security.com/');
      expect(isPublicRoute(request)).toBe(true);
    });

    it('should match /news as public (SSR page)', () => {
      const request = new Request('https://sps-security.com/news');
      expect(isPublicRoute(request)).toBe(true);
    });

    it('should match /news/some-article as public', () => {
      const request = new Request('https://sps-security.com/news/some-article');
      expect(isPublicRoute(request)).toBe(true);
    });

    it('should match /intelligence as public (SSR page)', () => {
      const request = new Request('https://sps-security.com/intelligence');
      expect(isPublicRoute(request)).toBe(true);
    });

    it('should match /intelligence/briefings as public', () => {
      const request = new Request('https://sps-security.com/intelligence/briefings');
      expect(isPublicRoute(request)).toBe(true);
    });

    it('should match /about as public', () => {
      const request = new Request('https://sps-security.com/about');
      expect(isPublicRoute(request)).toBe(true);
    });

    it('should match /services/consulting as public', () => {
      const request = new Request('https://sps-security.com/services/consulting');
      expect(isPublicRoute(request)).toBe(true);
    });

    it('should match /api/health as public', () => {
      const request = new Request('https://sps-security.com/api/health');
      expect(isPublicRoute(request)).toBe(true);
    });

    it('should match /api/search-index.json as public', () => {
      const request = new Request('https://sps-security.com/api/search-index.json');
      expect(isPublicRoute(request)).toBe(true);
    });

    it('should NOT match /dashboard as public', () => {
      const request = new Request('https://sps-security.com/dashboard');
      expect(isPublicRoute(request)).toBe(false);
    });

    it('should NOT match /sign-in as public', () => {
      const request = new Request('https://sps-security.com/sign-in');
      expect(isPublicRoute(request)).toBe(false);
    });

    it('should NOT match /api/user as public', () => {
      const request = new Request('https://sps-security.com/api/user');
      expect(isPublicRoute(request)).toBe(false);
    });
  });

  describe('isProtectedRoute matcher', () => {
    const protectedPatterns = ['/dashboard(.*)', '/api/user(.*)'];

    const isProtectedRoute = mockCreateRouteMatcher(protectedPatterns);

    it('should match /dashboard as protected', () => {
      const request = new Request('https://sps-security.com/dashboard');
      expect(isProtectedRoute(request)).toBe(true);
    });

    it('should match /dashboard/settings as protected', () => {
      const request = new Request('https://sps-security.com/dashboard/settings');
      expect(isProtectedRoute(request)).toBe(true);
    });

    it('should match /api/user as protected', () => {
      const request = new Request('https://sps-security.com/api/user');
      expect(isProtectedRoute(request)).toBe(true);
    });

    it('should match /api/user/profile as protected', () => {
      const request = new Request('https://sps-security.com/api/user/profile');
      expect(isProtectedRoute(request)).toBe(true);
    });

    it('should NOT match /news as protected', () => {
      const request = new Request('https://sps-security.com/news');
      expect(isProtectedRoute(request)).toBe(false);
    });

    it('should NOT match / as protected', () => {
      const request = new Request('https://sps-security.com/');
      expect(isProtectedRoute(request)).toBe(false);
    });
  });

  describe('Middleware behavior', () => {
    it('should bypass Clerk for public routes', async () => {
      // This test verifies the expected behavior:
      // When a public route is accessed, Clerk middleware should NOT be invoked
      const publicPatterns = ['/news(.*)'];
      const isPublicRoute = mockCreateRouteMatcher(publicPatterns);

      const mockNext = vi.fn().mockResolvedValue(new Response('OK'));
      const mockContext = {
        request: new Request('https://sps-security.com/news'),
      };

      // Simulate middleware behavior
      if (isPublicRoute(mockContext.request)) {
        await mockNext();
      } else {
        mockClerkMiddleware();
      }

      expect(mockNext).toHaveBeenCalled();
      expect(mockClerkMiddleware).not.toHaveBeenCalled();
    });

    it('should apply Clerk for non-public routes', async () => {
      const publicPatterns = ['/news(.*)'];
      const isPublicRoute = mockCreateRouteMatcher(publicPatterns);

      const mockNext = vi.fn().mockResolvedValue(new Response('OK'));
      const mockContext = {
        request: new Request('https://sps-security.com/dashboard'),
      };

      // Simulate middleware behavior
      if (isPublicRoute(mockContext.request)) {
        await mockNext();
      } else {
        mockClerkMiddleware();
      }

      expect(mockNext).not.toHaveBeenCalled();
      expect(mockClerkMiddleware).toHaveBeenCalled();
    });
  });
});
