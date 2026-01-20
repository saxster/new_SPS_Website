import { useState, useEffect } from 'preact/hooks';

interface Bookmark {
  article_slug: string;
  article_title: string;
  saved_at: string;
}

export default function SavedArticles() {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/user/bookmarks')
      .then(res => res.ok ? res.json() : { bookmarks: [] })
      .then(data => {
        setBookmarks(data.bookmarks || []);
        setLoading(false);
      })
      .catch(() => {
        setBookmarks([]);
        setLoading(false);
      });
  }, []);

  const removeBookmark = async (slug: string) => {
    try {
      const res = await fetch(`/api/user/bookmarks/${encodeURIComponent(slug)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setBookmarks(prev => prev.filter(b => b.article_slug !== slug));
      }
    } catch (err) {
      console.error('Failed to remove bookmark:', err);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div class="bg-neutral-900 border-2 border-neutral-800 p-6">
        <div class="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} class="h-16 bg-neutral-800 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (bookmarks.length === 0) {
    return (
      <div class="bg-neutral-900 border-2 border-neutral-800 p-12 text-center">
        <svg class="w-16 h-16 mx-auto text-neutral-700 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
        </svg>
        <h3 class="text-lg font-bold text-neutral-400 mb-2">NO SAVED ARTICLES</h3>
        <p class="text-sm text-neutral-600 mb-6">
          Bookmark articles from the intelligence feed to save them here for quick access.
        </p>
        <a
          href="/articles"
          class="inline-flex items-center gap-2 bg-primary-accent text-black px-4 py-2 font-bold text-sm uppercase tracking-wider hover:bg-primary-accent/80 transition-colors"
        >
          Browse Intelligence
        </a>
      </div>
    );
  }

  return (
    <div class="bg-neutral-900 border-2 border-neutral-800">
      <div class="p-4 border-b-2 border-neutral-800 flex items-center justify-between">
        <span class="text-sm font-bold text-neutral-400 uppercase tracking-wider">
          {bookmarks.length} Saved Article{bookmarks.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div class="divide-y divide-neutral-800">
        {bookmarks.map(bookmark => (
          <div key={bookmark.article_slug} class="p-4 flex items-center justify-between gap-4 group hover:bg-neutral-800/50 transition-colors">
            <a
              href={`/articles/${bookmark.article_slug}`}
              class="flex-1 min-w-0"
            >
              <h4 class="font-bold text-neutral-200 group-hover:text-primary-accent transition-colors truncate">
                {bookmark.article_title}
              </h4>
              <p class="text-xs text-neutral-600 font-mono mt-1">
                Saved {formatDate(bookmark.saved_at)}
              </p>
            </a>
            <button
              onClick={() => removeBookmark(bookmark.article_slug)}
              class="shrink-0 p-2 text-neutral-500 hover:text-red-400 hover:bg-red-900/20 transition-colors"
              title="Remove bookmark"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
