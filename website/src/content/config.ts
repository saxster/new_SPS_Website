import { defineCollection, z } from 'astro:content';

const blogCollection = defineCollection({
  schema: z.object({
    title: z.string(),
    pubDate: z.date(),
    author: z.string().optional(),
    description: z.string().optional(),
    image: z.object({
      url: z.string(),
      alt: z.string()
    }).optional(),
    tags: z.array(z.string()).optional()
  })
});

const intelligenceCollection = defineCollection({
  schema: z.object({
    title: z.string(),
    pubDate: z.date(),
    severity: z.enum(['Critical', 'High', 'Medium', 'Low', 'Optimized']).optional(),
    sector: z.string().optional(),
    tags: z.array(z.string()).optional(),
    source_urls: z.array(z.string()).optional(),
    analysis_engine: z.string().optional(),
    consensus_score: z.number().optional(),
    draft: z.boolean().default(false)
  })
});

const caseStudiesCollection = defineCollection({
  schema: z.object({
    title: z.string(),
    location: z.string().optional(),
    date: z.string().optional(), // String format for flexible date display
    summary: z.string().optional(),
    challenge: z.string().optional(),
    solution: z.string().optional(),
    outcome: z.array(z.string()).optional(), // Array of outcome points
    tags: z.array(z.string()).optional(),
    image: z.string().optional()
  })
});

const sectorsCollection = defineCollection({
  schema: z.object({
    title: z.string(),
    description: z.string(),
    icon: z.string().optional()
  })
});

const qnaCollection = defineCollection({
  schema: z.object({
    question: z.string(),
    category: z.string().optional(), // Made optional - some entries may lack this
    featured: z.boolean().default(false)
  })
});

// Dynamic Pages Collection
const pagesCollection = defineCollection({
  schema: z.object({
    title: z.string(),
    slug: z.string().optional(), // Optional - can be inferred from filename
    description: z.string().optional(),
    sections: z.array(z.any()).optional() // Flexible JSON structure for blocks
  })
});

export const collections = {
  'blog': blogCollection,
  'intelligence': intelligenceCollection,
  'casestudies': caseStudiesCollection,
  'sectors': sectorsCollection,
  'qna': qnaCollection,
  'pages': pagesCollection
};
