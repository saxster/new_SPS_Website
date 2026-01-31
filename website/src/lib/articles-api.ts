/**
 * API client for fetching auto-published articles from the SPS Brain backend.
 * Used by SSR pages to display articles stored in the database.
 */

// Backend API URL - defaults to localhost for development
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export interface Article {
    slug: string;
    title: string;
    description: string;
    category: string;
    content_type: string;
    body: string;
    tags: string[];
    published_date: string;
    author: string;
    image?: {
        src: string;
        alt: string;
    };
    council_verdict?: {
        decision: string;
        confidence: number;
        advocate_score: number;
        skeptic_score: number;
        guardian_score: number;
    };
}

export interface ArticleListResponse {
    articles: Article[];
    count: number;
}

/**
 * Fetch a single article by slug.
 */
export async function getArticleBySlug(slug: string): Promise<Article | null> {
    try {
        const response = await fetch(`${BACKEND_URL}/articles/${slug}`);

        if (!response.ok) {
            if (response.status === 404) {
                return null;
            }
            throw new Error(`Failed to fetch article: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`Error fetching article ${slug}:`, error);
        return null;
    }
}

/**
 * Fetch list of published articles with pagination.
 */
export async function getArticles(
    limit: number = 20,
    offset: number = 0
): Promise<Article[]> {
    try {
        const response = await fetch(
            `${BACKEND_URL}/articles?limit=${limit}&offset=${offset}`
        );

        if (!response.ok) {
            throw new Error(`Failed to fetch articles: ${response.status}`);
        }

        const data: ArticleListResponse = await response.json();
        return data.articles;
    } catch (error) {
        console.error('Error fetching articles:', error);
        return [];
    }
}

/**
 * Get content type badge styling.
 */
export function getContentTypeStyle(contentType: string): string {
    const styles: Record<string, string> = {
        'News': 'bg-blue-600 text-white',
        'Guide': 'bg-green-600 text-white',
        'Analysis': 'bg-purple-600 text-white',
        'Review': 'bg-orange-600 text-white',
    };
    return styles[contentType] || 'bg-neutral-600 text-white';
}

/**
 * Get category badge styling.
 */
export function getCategoryStyle(category: string): string {
    const styles: Record<string, string> = {
        'Security': 'bg-red-600 text-white',
        'Technology': 'bg-cyan-600 text-white',
        'Compliance': 'bg-amber-600 text-black',
        'Industry': 'bg-indigo-600 text-white',
    };
    return styles[category] || 'bg-neutral-600 text-white';
}
