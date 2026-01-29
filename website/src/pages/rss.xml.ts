import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIRoute } from 'astro';

export const GET: APIRoute = async (context) => {
  // Fetch both blog and intelligence collections
  const blogPosts = await getCollection('blog');
  const intelligenceBriefings = await getCollection('intelligence', ({ data }) => !data.draft);

  // Combine and sort by date
  const allItems = [
    ...blogPosts.map(post => ({
      title: post.data.title,
      pubDate: post.data.pubDate,
      description: post.data.description || post.body.substring(0, 300) + '...',
      link: `/articles/${post.slug}/`,
      categories: post.data.tags || [],
    })),
    ...intelligenceBriefings.map(briefing => ({
      title: briefing.data.title,
      pubDate: briefing.data.pubDate,
      description: briefing.body.substring(0, 300) + '...',
      link: `/intelligence/briefings/${briefing.slug}/`,
      categories: briefing.data.tags || [],
    })),
  ].sort((a, b) => b.pubDate.valueOf() - a.pubDate.valueOf());

  return rss({
    // Channel metadata
    title: 'SPS Security Intelligence Feed',
    description: 'Authoritative security intelligence, compliance guidance, and threat analysis from India\'s trusted security platform. Trusted Since 1965.',
    site: context.site || 'https://sukhi.in',
    
    // Items
    items: allItems,
    
    // Optional: Add custom XML
    customData: `<language>en-in</language>
<copyright>© ${new Date().getFullYear()} SPS - A Sukhi Enterprise. All rights reserved.</copyright>
<managingEditor>intelligence@sukhi.in (SPS Intelligence Team)</managingEditor>
<webMaster>tech@sukhi.in (SPS Technical Team)</webMaster>
<category>Security</category>
<category>Compliance</category>
<category>Threat Intelligence</category>`,
    
    // Stylesheet for browser viewing
    stylesheet: '/rss-styles.xsl',
  });
};
