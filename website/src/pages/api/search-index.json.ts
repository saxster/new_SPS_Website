import { getCollection } from 'astro:content';

export async function GET() {
  const blogs = await getCollection('blog');
  const sectors = await getCollection('sectors');
  const cases = await getCollection('casestudies');

  const searchIndex = [
    // Static Pages
    { title: "Home Command", type: "PAGE", url: "/", description: "Main Dashboard" },
    { title: "About SPS", type: "PAGE", url: "/about", description: "History and Doctrine" },
    { title: "Services & Methodology", type: "PAGE", url: "/services", description: "Vetting and Deployment Protocols" },
    { title: "Command Centre", type: "PAGE", url: "/contact", description: "Contact and Emergency" },
    { title: "Tactical Tools", type: "TOOL", url: "/tools", description: "Utilities Index" },
    { title: "Threat Calculus Engine", type: "TOOL", url: "/tools/risk-calculator", description: "Vulnerability Assessment" },
    { title: "Officers / Leadership", type: "PAGE", url: "/officers", description: "Command Structure" },

    // Dynamic Content
    ...blogs.map(post => ({
      title: post.data.title,
      type: "INTEL",
      url: `/articles/${post.slug}`,
      description: post.data.description
    })),
    ...sectors.map(sector => ({
      title: `${sector.data.title} Protocol`,
      type: "SECTOR",
      url: `/sectors/${sector.slug}`,
      description: sector.data.description
    })),
    ...cases.map(c => ({
      title: `Case: ${c.data.title}`,
      type: "CASE",
      url: `/operations/${c.slug}`,
      description: c.data.summary
    }))
  ];

  return new Response(JSON.stringify(searchIndex), {
    status: 200,
    headers: {
      "Content-Type": "application/json"
    }
  });
}