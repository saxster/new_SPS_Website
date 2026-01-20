import { useState, useMemo } from 'preact/hooks';

interface Article {
  slug: string;
  title: string;
  description: string;
  pubDate: string;
  category?: string;
  tags: string[];
  megatrend?: string;
}

interface ArticleFiltersProps {
  articles: Article[];
  categories: string[];
  megatrends: string[];
  itemsPerPage?: number;
}

const ITEMS_PER_PAGE = 12;

export default function ArticleFilters({
  articles,
  categories,
  megatrends,
  itemsPerPage = ITEMS_PER_PAGE,
}: ArticleFiltersProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedMegatrend, setSelectedMegatrend] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest'>('newest');
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  // Filter and sort articles
  const filteredArticles = useMemo(() => {
    let result = [...articles];

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (article) =>
          article.title.toLowerCase().includes(query) ||
          article.description.toLowerCase().includes(query) ||
          article.tags.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      result = result.filter((article) => article.category === selectedCategory);
    }

    // Filter by megatrend
    if (selectedMegatrend !== 'all') {
      result = result.filter((article) => article.megatrend === selectedMegatrend);
    }

    // Sort
    result.sort((a, b) => {
      const dateA = new Date(a.pubDate).valueOf();
      const dateB = new Date(b.pubDate).valueOf();
      return sortBy === 'newest' ? dateB - dateA : dateA - dateB;
    });

    return result;
  }, [articles, selectedCategory, selectedMegatrend, sortBy, searchQuery]);

  // Pagination
  const totalPages = Math.ceil(filteredArticles.length / itemsPerPage);
  const paginatedArticles = filteredArticles.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Reset page when filters change
  const handleFilterChange = (setter: (value: string) => void, value: string) => {
    setter(value);
    setCurrentPage(1);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  const getCategoryClass = (category?: string) => {
    switch (category) {
      case 'Critical':
        return 'status-badge--critical';
      case 'Compliance':
        return 'status-badge--compliance';
      default:
        return 'status-badge--verified';
    }
  };

  return (
    <div class="space-y-8">
      {/* Filters Row */}
      <div class="flex flex-col lg:flex-row gap-4 p-6 bg-neutral-900 border-2 border-neutral-800">
        {/* Search */}
        <div class="flex-1">
          <label for="article-search" class="sr-only">
            Search articles
          </label>
          <input
            id="article-search"
            type="search"
            placeholder="SEARCH ARTICLES..."
            value={searchQuery}
            onInput={(e) => handleFilterChange(setSearchQuery, (e.target as HTMLInputElement).value)}
            class="w-full bg-black border-2 border-neutral-700 text-white p-3 text-sm focus:border-primary-accent focus:outline-none placeholder-neutral-500 uppercase tracking-wide font-mono"
          />
        </div>

        {/* Category Filter */}
        <div class="w-full lg:w-48">
          <label for="category-filter" class="sr-only">
            Filter by category
          </label>
          <select
            id="category-filter"
            value={selectedCategory}
            onChange={(e) => handleFilterChange(setSelectedCategory, (e.target as HTMLSelectElement).value)}
            class="w-full bg-black border-2 border-neutral-700 text-white p-3 text-sm focus:border-primary-accent focus:outline-none uppercase tracking-wide font-mono cursor-pointer"
          >
            <option value="all">ALL CATEGORIES</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        {/* Megatrend Filter */}
        <div class="w-full lg:w-56">
          <label for="megatrend-filter" class="sr-only">
            Filter by megatrend
          </label>
          <select
            id="megatrend-filter"
            value={selectedMegatrend}
            onChange={(e) => handleFilterChange(setSelectedMegatrend, (e.target as HTMLSelectElement).value)}
            class="w-full bg-black border-2 border-neutral-700 text-white p-3 text-sm focus:border-primary-accent focus:outline-none uppercase tracking-wide font-mono cursor-pointer"
          >
            <option value="all">ALL MEGATRENDS</option>
            {megatrends.map((trend) => (
              <option key={trend} value={trend}>
                {trend.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        {/* Sort */}
        <div class="w-full lg:w-40">
          <label for="sort-filter" class="sr-only">
            Sort articles
          </label>
          <select
            id="sort-filter"
            value={sortBy}
            onChange={(e) => setSortBy((e.target as HTMLSelectElement).value as 'newest' | 'oldest')}
            class="w-full bg-black border-2 border-neutral-700 text-white p-3 text-sm focus:border-primary-accent focus:outline-none uppercase tracking-wide font-mono cursor-pointer"
          >
            <option value="newest">NEWEST</option>
            <option value="oldest">OLDEST</option>
          </select>
        </div>
      </div>

      {/* Results Count */}
      <div class="text-sm text-neutral-500 font-mono">
        SHOWING {paginatedArticles.length} OF {filteredArticles.length} RECORDS
        {filteredArticles.length !== articles.length && (
          <span class="text-primary-accent ml-2">(FILTERED)</span>
        )}
      </div>

      {/* Articles Grid */}
      {paginatedArticles.length === 0 ? (
        <div class="text-center py-16 border-2 border-neutral-800 bg-neutral-900/50">
          <p class="text-neutral-400 text-lg mb-4">NO RECORDS FOUND</p>
          <p class="text-neutral-600 text-sm">
            Try adjusting your filters or search query.
          </p>
          <button
            onClick={() => {
              setSelectedCategory('all');
              setSelectedMegatrend('all');
              setSearchQuery('');
              setCurrentPage(1);
            }}
            class="mt-6 text-primary-accent text-sm font-mono hover:underline"
          >
            CLEAR ALL FILTERS
          </button>
        </div>
      ) : (
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {paginatedArticles.map((article) => (
            <article
              key={article.slug}
              class="brutalist-card group relative overflow-hidden flex flex-col h-full bg-neutral-900 border-neutral-800 hover:border-primary-accent transition-colors"
            >
              <div class="flex items-center gap-3 mb-4 border-b border-neutral-800 pb-3">
                <span class={`status-badge ${getCategoryClass(article.category)}`}>
                  <span class="status-indicator"></span>
                  {article.category?.toUpperCase() || 'BRIEF'}
                </span>
                <span class="text-mono text-xs text-neutral-500 ml-auto">
                  {formatDate(article.pubDate)}
                </span>
              </div>

              <h3 class="text-xl font-bold text-white mb-3 group-hover:text-primary-accent transition-colors">
                <a href={`/articles/${article.slug}`}>
                  <span class="absolute inset-0 z-10"></span>
                  {article.title}
                </a>
              </h3>

              <p class="text-neutral-400 text-sm mb-6 line-clamp-3 leading-relaxed flex-grow">
                {article.description}
              </p>

              {article.megatrend && (
                <div class="mb-4">
                  <span class="text-[10px] font-mono text-neutral-500 uppercase tracking-widest px-2 py-1 bg-neutral-800 border border-neutral-700">
                    {article.megatrend}
                  </span>
                </div>
              )}

              <div class="flex items-center justify-between relative z-20 mt-auto pt-4 border-t border-neutral-800">
                <span class="text-primary-accent text-xs font-bold uppercase tracking-wider group-hover:underline">
                  Read Analysis
                </span>
                <span class="text-neutral-600 text-lg">→</span>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <nav
          class="flex items-center justify-center gap-2 pt-8"
          aria-label="Pagination"
        >
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            class="px-4 py-2 text-sm font-mono bg-neutral-900 border-2 border-neutral-700 text-neutral-400 hover:border-primary-accent hover:text-primary-accent disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous page"
          >
            ← PREV
          </button>

          <div class="flex gap-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                class={`w-10 h-10 text-sm font-mono border-2 transition-colors ${
                  page === currentPage
                    ? 'bg-primary-accent text-black border-primary-accent'
                    : 'bg-neutral-900 border-neutral-700 text-neutral-400 hover:border-primary-accent hover:text-primary-accent'
                }`}
                aria-label={`Page ${page}`}
                aria-current={page === currentPage ? 'page' : undefined}
              >
                {page}
              </button>
            ))}
          </div>

          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            class="px-4 py-2 text-sm font-mono bg-neutral-900 border-2 border-neutral-700 text-neutral-400 hover:border-primary-accent hover:text-primary-accent disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Next page"
          >
            NEXT →
          </button>
        </nav>
      )}
    </div>
  );
}
