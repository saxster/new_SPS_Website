import type { APIRoute } from 'astro';

export const GET: APIRoute = async ({ request }) => {
  const url = new URL(request.url);
  const topic = url.searchParams.get('topic') || 'all';
  const sector = url.searchParams.get('sector') || 'all';

  // Sector-specific keyword mapping
  const SECTOR_KEYWORDS: Record<string, string> = {
    'jewellery': '("gold heist" OR "jewellery robbery" OR "diamond theft" OR "zaveri bazaar")',
    'finance': '("bank robbery" OR "atm fraud" OR "heist" OR "nbfc robbery")',
    'corporate': '("data breach" OR "corporate espionage" OR "office fire" OR "it park")',
    'industrial': '("factory fire" OR "labor strike" OR "industrial accident" OR "warehouse")',
    'healthcare': '("hospital fire" OR "oxygen leak" OR "medical equipment theft")',
    'residential': '("society robbery" OR "apartment theft" OR "domestic help theft")'
  };

  const sectorQuery = SECTOR_KEYWORDS[sector] ? `${SECTOR_KEYWORDS[sector]} AND ` : '';

  // Advanced Google News Query for Indian Security Context
  const BASE_QUERY = `
    ${sectorQuery}( 
      "riot" OR "protest" OR "strike" OR "bandh" OR "morcha" OR "hartal" OR 
      "curfew" OR "section 144" OR "lathi charge" OR "tear gas" OR
      "terror" OR "blast" OR "ied" OR "militant" OR "encouter" OR
      "fire" OR "explosion" OR "building collapse" OR "gas leak" OR
      "traffic jam" OR "road block" OR "gridlock" OR "diversion"
    ) location:India
  `.replace(/\s+/g, ' ').trim();

  const GOOGLE_NEWS_RSS = `https://news.google.com/rss/search?q=${encodeURIComponent(BASE_QUERY)}&hl=en-IN&gl=IN&ceid=IN:en`;

  try {
    const response = await fetch(GOOGLE_NEWS_RSS);
    const xmlText = await response.text();

    // Simple Regex XML Parser (faster/lighter than installing a DOM parser for this use case)
    const items = [];
    const itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let match;

    while ((match = itemRegex.exec(xmlText)) !== null) {
      const itemContent = match[1];
      
      const titleMatch = itemContent.match(/<title>([\s\S]*?)<\/title>/);
      const linkMatch = itemContent.match(/<link>([\s\S]*?)<\/link>/);
      const dateMatch = itemContent.match(/<pubDate>([\s\S]*?)<\/pubDate>/);
      const descMatch = itemContent.match(/<description>([\s\S]*?)<\/description>/);
      const sourceMatch = itemContent.match(/<source[^>]*>([\s\S]*?)<\/source>/);

      if (titleMatch && linkMatch) {
        const title = decodeHtml(titleMatch[1]);
        const description = descMatch ? decodeHtml(cleanDescription(descMatch[1])) : '';
        
        // Auto-Categorization Logic
        let category = 'GENERAL';
        let severity = 'low';

        const t = (title + ' ' + description).toLowerCase();

        if (t.includes('terror') || t.includes('blast') || t.includes('ied') || t.includes('kill')) {
          category = 'PUBLIC SAFETY';
          severity = 'critical';
        } else if (t.includes('riot') || t.includes('clash') || t.includes('violence') || t.includes('mob')) {
          category = 'CIVIL UNREST';
          severity = 'high';
        } else if (t.includes('fire') || t.includes('collapse') || t.includes('gas leak')) {
          category = 'HAZARD';
          severity = 'high';
        } else if (t.includes('traffic') || t.includes('jam') || t.includes('stuck') || t.includes('bandh') || t.includes('strike')) {
          category = 'DISRUPTION';
          severity = 'medium';
        }

        items.push({
          title,
          url: linkMatch[1],
          time: dateMatch ? new Date(dateMatch[1]).toISOString() : new Date().toISOString(),
          source: sourceMatch ? sourceMatch[1] : 'Google News',
          category,
          severity
        });
      }
    }

    return new Response(JSON.stringify({
      status: 'success',
      timestamp: new Date().toISOString(),
      count: items.length,
      articles: items
    }), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=600' // Cache for 10 minutes
      }
    });

  } catch (error) {
    return new Response(JSON.stringify({
      status: 'error',
      message: error instanceof Error ? error.message : 'Unknown error'
    }), { status: 500 });
  }
};

// Helpers
function decodeHtml(html: string) {
  return html
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function cleanDescription(html: string) {
  // Remove the Google News "View full coverage" link and standard HTML tags
  return html.replace(/<a[^>]*>.*?<\/a>/g, '').replace(/<[^>]*>/g, '');
}
