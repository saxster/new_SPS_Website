import type { APIRoute } from 'astro';

// Server-rendered API route
export const prerender = false;

// Note: In production, this would connect to SQLite via content_brain.py
// For now, we use a simple in-memory store (per-session)
// TODO: Implement proper database connection

interface Bookmark {
  article_slug: string;
  article_title: string;
  saved_at: string;
}

// Temporary in-memory store (for development)
const userBookmarks = new Map<string, Bookmark[]>();

export const GET: APIRoute = async ({ locals }) => {
  try {
    const auth = locals.auth();

    if (!auth.userId) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const bookmarks = userBookmarks.get(auth.userId) || [];

    return new Response(JSON.stringify({ bookmarks }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error fetching bookmarks:', error);
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
    const { article_slug, article_title } = body;

    if (!article_slug || typeof article_slug !== 'string') {
      return new Response(JSON.stringify({ error: 'Invalid article slug' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const currentBookmarks = userBookmarks.get(auth.userId) || [];

    // Check if already bookmarked
    if (currentBookmarks.some(b => b.article_slug === article_slug)) {
      return new Response(JSON.stringify({ error: 'Already bookmarked' }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const newBookmark: Bookmark = {
      article_slug,
      article_title: article_title || article_slug,
      saved_at: new Date().toISOString(),
    };

    userBookmarks.set(auth.userId, [...currentBookmarks, newBookmark]);

    return new Response(JSON.stringify({ success: true, bookmark: newBookmark }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error saving bookmark:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
