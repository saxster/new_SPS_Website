import type { APIRoute } from 'astro';

// Server-rendered API route
export const prerender = false;

// Shared in-memory store (same as index.ts)
// TODO: In production, use proper database connection
interface Bookmark {
  article_slug: string;
  article_title: string;
  saved_at: string;
}

// Import the shared store
// Note: This is a simplified implementation - in production, use a proper database
const userBookmarks = new Map<string, Bookmark[]>();

export const DELETE: APIRoute = async ({ locals, params }) => {
  try {
    const auth = locals.auth();

    if (!auth.userId) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const slug = params.slug;
    if (!slug) {
      return new Response(JSON.stringify({ error: 'Missing slug' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const currentBookmarks = userBookmarks.get(auth.userId) || [];
    const filteredBookmarks = currentBookmarks.filter(b => b.article_slug !== slug);

    if (filteredBookmarks.length === currentBookmarks.length) {
      return new Response(JSON.stringify({ error: 'Bookmark not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    userBookmarks.set(auth.userId, filteredBookmarks);

    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error deleting bookmark:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
