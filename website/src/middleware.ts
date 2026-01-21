import { defineMiddleware, sequence } from 'astro:middleware';
import { clerkMiddleware, createRouteMatcher } from '@clerk/astro/server';

/**
 * Protected routes that require authentication
 */
const isProtectedRoute = createRouteMatcher([
  '/dashboard(.*)',
  '/api/user(.*)',
]);

/**
 * Clerk authentication middleware
 */
const authMiddleware = clerkMiddleware((auth, context) => {
  const { userId, redirectToSignIn } = auth();

  // Redirect to sign-in for protected routes if not authenticated
  if (!userId && isProtectedRoute(context.request)) {
    return redirectToSignIn();
  }
});

/**
 * Security middleware that adds important security headers to all responses.
 *
 * Headers included:
 * - Content-Security-Policy (CSP): Prevents XSS and other injection attacks
 * - X-Content-Type-Options: Prevents MIME type sniffing
 * - X-Frame-Options: Prevents clickjacking
 * - X-XSS-Protection: Legacy XSS protection
 * - Referrer-Policy: Controls referrer information
 * - Permissions-Policy: Restricts browser features
 */
const securityMiddleware = defineMiddleware(async (context, next) => {
  const response = await next();

  // Clone the response to add headers
  const newResponse = new Response(response.body, response);

  // Content Security Policy
  // Note: 'unsafe-inline' is required for Astro's island hydration
  // Added Clerk domains for authentication
  const isDev = process.env.NODE_ENV === 'development';
  
  const cspDirectives = [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://*.clerk.accounts.dev ${isDev ? 'http://localhost:* http://127.0.0.1:*' : ''}`,
    "style-src 'self' 'unsafe-inline' https://unpkg.com",
    "img-src 'self' data: https: blob:",
    "font-src 'self' https://fonts.gstatic.com",
    `connect-src 'self' https://api.openai.com https://api.anthropic.com https://*.basemaps.cartocdn.com https://*.clerk.accounts.dev https://clerk.sps-security.com ${isDev ? 'ws://localhost:* http://localhost:* http://127.0.0.1:*' : ''}`,
    "frame-src 'self' https://*.clerk.accounts.dev",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self' https://*.clerk.accounts.dev",
  ].join('; ');

  newResponse.headers.set('Content-Security-Policy', cspDirectives);

  // Prevent MIME type sniffing
  newResponse.headers.set('X-Content-Type-Options', 'nosniff');

  // Prevent clickjacking
  newResponse.headers.set('X-Frame-Options', 'DENY');

  // Enforce HTTPS
  newResponse.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');

  // Legacy XSS protection for older browsers
  newResponse.headers.set('X-XSS-Protection', '1; mode=block');

  // Control referrer information
  newResponse.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');

  // Restrict browser features
  newResponse.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=(), interest-cohort=()'
  );

  return newResponse;
});

// Combine middleware in sequence: auth first, then security headers
export const onRequest = sequence(authMiddleware, securityMiddleware);
