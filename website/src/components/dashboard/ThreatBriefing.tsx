import { useState, useEffect } from 'preact/hooks';

interface Article {
  slug: string;
  title: string;
  description: string;
  sector: string;
  publishedAt: string;
  contentType: string;
}

interface Props {
  articles: Article[];
}

export default function ThreatBriefing({ articles }: Props) {
  const [userSectors, setUserSectors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch user's sector preferences
    fetch('/api/user/preferences')
      .then(res => res.ok ? res.json() : { sectors: [] })
      .then(data => {
        setUserSectors(data.sectors || []);
        setLoading(false);
      })
      .catch(() => {
        setUserSectors([]);
        setLoading(false);
      });
  }, []);

  // Filter articles based on user's sector preferences
  const filteredArticles = userSectors.length > 0
    ? articles.filter(a => userSectors.includes(a.sector))
    : articles;

  // Get content type badge style
  const getContentTypeBadge = (type: string) => {
    const styles: Record<string, string> = {
      'Threat Alert': 'bg-red-900/30 text-red-400 border-red-500/30',
      'Analysis': 'bg-blue-900/30 text-blue-400 border-blue-500/30',
      'Guide': 'bg-green-900/30 text-green-400 border-green-500/30',
      'Case Study': 'bg-purple-900/30 text-purple-400 border-purple-500/30',
      'Regulation Update': 'bg-amber-900/30 text-amber-400 border-amber-500/30',
    };
    return styles[type] || 'bg-neutral-800 text-neutral-400 border-neutral-600';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  if (loading) {
    return (
      <div class="bg-neutral-900 border-2 border-neutral-800 p-6">
        <div class="animate-pulse space-y-4">
          <div class="h-4 bg-neutral-800 rounded w-1/3"></div>
          <div class="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} class="h-20 bg-neutral-800 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div class="bg-neutral-900 border-2 border-neutral-800">
      <div class="p-4 border-b-2 border-neutral-800 flex items-center justify-between">
        <h3 class="text-sm font-bold text-neutral-400 uppercase tracking-wider">
          Latest Intelligence
        </h3>
        {userSectors.length > 0 && (
          <span class="text-xs text-primary-accent font-mono">
            FILTERED: {userSectors.length} SECTORS
          </span>
        )}
      </div>

      {filteredArticles.length === 0 ? (
        <div class="p-8 text-center">
          <p class="text-neutral-500 mb-4">
            {userSectors.length > 0
              ? 'No articles found for your selected sectors.'
              : 'No articles available.'}
          </p>
          {userSectors.length === 0 && (
            <p class="text-xs text-neutral-600">
              Select sectors in preferences to personalize your briefing.
            </p>
          )}
        </div>
      ) : (
        <div class="divide-y divide-neutral-800">
          {filteredArticles.slice(0, 5).map(article => (
            <a
              key={article.slug}
              href={`/articles/${article.slug}`}
              class="block p-4 hover:bg-neutral-800/50 transition-colors group"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-2">
                    <span class={`text-[10px] font-bold px-2 py-0.5 border ${getContentTypeBadge(article.contentType)}`}>
                      {article.contentType.toUpperCase()}
                    </span>
                    <span class="text-[10px] text-neutral-600 font-mono">
                      {article.sector.toUpperCase()}
                    </span>
                  </div>
                  <h4 class="font-bold text-neutral-200 group-hover:text-primary-accent transition-colors line-clamp-2">
                    {article.title}
                  </h4>
                  <p class="text-sm text-neutral-500 mt-1 line-clamp-2">
                    {article.description}
                  </p>
                </div>
                <div class="text-right shrink-0">
                  <p class="text-xs text-neutral-600 font-mono">
                    {formatDate(article.publishedAt)}
                  </p>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}

      {filteredArticles.length > 5 && (
        <div class="p-4 border-t-2 border-neutral-800">
          <a
            href="/articles"
            class="text-sm text-primary-accent hover:text-primary-accent/80 font-mono uppercase tracking-wider"
          >
            View All Intel →
          </a>
        </div>
      )}
    </div>
  );
}
