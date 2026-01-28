import { getCollection } from 'astro:content';
import { normalizeTags, type SearchIndexItem } from '../../utils/commandPaletteUtils';

export async function GET() {
  const blogs = await getCollection('blog');
  const sectors = await getCollection('sectors');
  const cases = await getCollection('casestudies');
  const intelligence = await getCollection('intelligence', ({ data }) => !data.draft);
  const qna = await getCollection('qna');

  const searchIndex: SearchIndexItem[] = [
    // Static Pages
    { title: "Home Command", type: "PAGE", url: "/", description: "Main Dashboard", tags: ["home", "dashboard"] },
    { title: "About SPS", type: "PAGE", url: "/about", description: "History and Doctrine", tags: ["about", "history", "company"] },
    { title: "Services & Methodology", type: "PAGE", url: "/services", description: "Vetting and Deployment Protocols", tags: ["services", "methodology", "vetting"] },
    { title: "Command Centre", type: "PAGE", url: "/contact", description: "Contact and Emergency", tags: ["contact", "emergency", "support"] },
    { title: "Tactical Tools", type: "TOOL", url: "/tools", description: "Utilities Index", tags: ["tools", "utilities"] },
    { title: "Threat Calculus Engine", type: "TOOL", url: "/tools/risk-calculator", description: "Vulnerability Assessment", tags: ["risk", "calculator", "assessment"] },
    { title: "Compliance Calculator", type: "TOOL", url: "/tools/compliance-calculator", description: "PSARA & Regulatory Compliance Checker", tags: ["compliance", "psara", "calculator", "legal"] },
    { title: "Storage Calculator", type: "TOOL", url: "/tools/storage-calculator", description: "CCTV Storage Requirements Calculator", tags: ["storage", "cctv", "calculator"] },
    { title: "Officers / Leadership", type: "PAGE", url: "/officers", description: "Command Structure", tags: ["officers", "leadership", "team"] },

    // Blog Articles (type: ARTICLE)
    ...blogs.map(post => ({
      title: post.data.title,
      type: "ARTICLE" as const,
      url: `/articles/${post.slug}`,
      description: post.data.description || '',
      tags: normalizeTags(post.data.tags),
      pubDate: post.data.pubDate?.toISOString()
    })),

    // Intelligence Reports (type: INTEL)
    ...intelligence.map(intel => ({
      title: intel.data.title,
      type: "INTEL" as const,
      url: `/intelligence/${intel.slug}`,
      description: intel.data.title,
      sector: intel.data.sector?.toLowerCase(),
      tags: normalizeTags(intel.data.tags),
      severity: intel.data.severity?.toLowerCase(),
      pubDate: intel.data.pubDate?.toISOString()
    })),

    // Sectors
    ...sectors.map(sector => ({
      title: `${sector.data.title} Protocol`,
      type: "SECTOR" as const,
      url: `/sectors/${sector.slug}`,
      description: sector.data.description,
      sector: sector.slug.toLowerCase(),
      tags: [sector.slug.toLowerCase(), 'sector', 'protocol']
    })),

    // Case Studies
    ...cases.map(c => ({
      title: `Case: ${c.data.title}`,
      type: "CASE" as const,
      url: `/operations/${c.slug}`,
      description: c.data.summary || '',
      tags: normalizeTags(c.data.tags)
    })),

    // Q&A
    ...qna.map(q => ({
      title: q.data.question,
      type: "QNA" as const,
      url: `/qna/${q.slug}`,
      description: q.data.question,
      category: q.data.category?.toLowerCase(),
      tags: ['qna', 'question', 'answer']
    }))
  ];

  return new Response(JSON.stringify(searchIndex), {
    status: 200,
    headers: {
      "Content-Type": "application/json"
    }
  });
}