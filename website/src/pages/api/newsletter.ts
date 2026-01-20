import type { APIRoute } from 'astro';
import {
  validateOrigin,
  createCsrfResponse,
  DEFAULT_ALLOWED_ORIGINS,
} from '../../utils/security';

// Server-rendered API route
export const prerender = false;

/**
 * Newsletter Subscription API Endpoint
 *
 * Handles newsletter signups with optional sector preferences.
 * Currently stores to a simple file-based log, but can be extended
 * to integrate with email services (SendGrid, Mailchimp, Resend, etc.)
 */

interface NewsletterRequest {
  email: string;
  sectors?: string[];
}

// Simple email validation
const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

// Rate limiting (in-memory, resets on server restart)
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 5;
const RATE_WINDOW_MS = 60 * 60 * 1000; // 1 hour

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

export const POST: APIRoute = async ({ request, clientAddress }) => {
  // CSRF protection: validate origin
  const origin = request.headers.get('origin');
  if (!validateOrigin(origin, DEFAULT_ALLOWED_ORIGINS)) {
    return createCsrfResponse();
  }

  try {
    // Rate limiting
    const ip = clientAddress || 'unknown';
    if (!checkRateLimit(ip)) {
      return new Response(
        JSON.stringify({ error: 'Too many requests. Please try again later.' }),
        { status: 429, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Parse request body
    const body: NewsletterRequest = await request.json();
    const { email, sectors = [] } = body;

    // Validate email
    if (!email || typeof email !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Email address is required.' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (!isValidEmail(email)) {
      return new Response(
        JSON.stringify({ error: 'Please provide a valid email address.' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Validate sectors (if provided)
    const validSectors = [
      'jewellery',
      'education',
      'healthcare',
      'finance',
      'cyber',
      'corporate',
      'industrial',
      'retail',
      'hospitality',
      'residential',
    ];

    const sanitizedSectors = Array.isArray(sectors)
      ? sectors.filter((s): s is string => typeof s === 'string' && validSectors.includes(s))
      : [];

    // Log subscription (in production, send to email service)
    const subscription = {
      email: email.toLowerCase().trim(),
      sectors: sanitizedSectors,
      subscribedAt: new Date().toISOString(),
      ip: ip.slice(0, 7) + '***', // Partially anonymize IP
    };

    // TODO: Replace with actual email service integration
    // Examples:
    // - SendGrid: await sendgrid.addContact(subscription)
    // - Mailchimp: await mailchimp.lists.addListMember(listId, {...})
    // - Resend: await resend.audiences.addContact(audienceId, {...})

    console.log('[Newsletter] New subscription:', subscription);

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Successfully subscribed to SPS Intelligence Briefings.',
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('[Newsletter] Error:', error);
    return new Response(
      JSON.stringify({ error: 'An unexpected error occurred. Please try again.' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
};

// Handle unsupported methods
export const ALL: APIRoute = async () => {
  return new Response(
    JSON.stringify({ error: 'Method not allowed' }),
    { status: 405, headers: { 'Content-Type': 'application/json' } }
  );
};
