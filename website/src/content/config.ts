import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
	type: 'content',
	schema: z.object({
		title: z.string(),
		description: z.string(),
		pubDate: z.coerce.date(),
		author: z.string().default('SPS Editorial Board'),
		image: z.string().optional(),
		tags: z.array(z.string()),
        category: z.string().optional(),
        contentType: z.string().optional(),
        wordCount: z.number().optional(),
        qualityScore: z.number().optional(),
        megatrend: z.enum([
            'Intelligent Automation',
            'Cyber-Physical Convergence',
            'Perimeter & Detection',
            'Identity & Access',
            'Strategic Risk'
        ]).optional(),
        executive_summary: z.array(z.string()).optional(),
        draft: z.boolean().default(false),
	}),
});

const casestudies = defineCollection({
    type: 'content',
    schema: z.object({
        title: z.string(),
        location: z.string(),
        date: z.string(),
        summary: z.string(),
        challenge: z.string(),
        solution: z.string(),
        outcome: z.array(z.string()),
        tags: z.array(z.string()),
    })
});

const sectors = defineCollection({
    type: 'content',
    schema: z.object({
        title: z.string(),
        icon: z.string().optional(),
        description: z.string(),
        risks: z.array(z.string()),
        regulations: z.array(z.string()),
    })
});

const qna = defineCollection({
    type: 'content',
    schema: z.object({
        question: z.string(),
        author: z.string(),
        role: z.string(),
        sector: z.string(),
        date: z.coerce.date(),
        answer: z.string().optional(),
        answeredBy: z.string(),
        tags: z.array(z.string()),
    })
});

const intelligence = defineCollection({
    type: 'content',
    schema: z.object({
        title: z.string(),
        pubDate: z.coerce.date(),
        severity: z.enum(['Critical', 'High', 'Medium', 'Low']),
        sector: z.string(),
        tags: z.array(z.string()),
        source_urls: z.array(z.string()),
        analysis_engine: z.string().default('SPS Consensus Engine v1.0'),
        consensus_score: z.number().min(0).max(100),
        draft: z.boolean().default(false),
    })
});

export const collections = { blog, casestudies, sectors, qna, intelligence };