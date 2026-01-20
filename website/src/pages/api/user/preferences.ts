import type { APIRoute } from 'astro';

// Server-rendered API route
export const prerender = false;

// Note: In production, this would connect to SQLite via content_brain.py
// For now, we use a simple in-memory store (per-session)
// TODO: Implement proper database connection

// Temporary in-memory store (for development)
const userPreferences = new Map<string, string[]>();

export const GET: APIRoute = async ({ locals }) => {
  try {
    const auth = locals.auth();

    if (!auth.userId) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const sectors = userPreferences.get(auth.userId) || [];

    return new Response(JSON.stringify({ sectors }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error fetching preferences:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};

export const POST: APIRoute = async ({ locals, request }) => {
  try {
    const auth = locals.auth();

    if (!auth.userId) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();
    const sectors = body.sectors;

    if (!Array.isArray(sectors)) {
      return new Response(JSON.stringify({ error: 'Invalid sectors format' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Validate sectors (basic sanitization)
    const sanitizedSectors = sectors
      .filter((s: unknown): s is string => typeof s === 'string')
      .map(s => s.trim().toLowerCase())
      .slice(0, 20); // Max 20 sectors

    userPreferences.set(auth.userId, sanitizedSectors);

    return new Response(JSON.stringify({ success: true, sectors: sanitizedSectors }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error saving preferences:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
