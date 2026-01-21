import fs from 'node:fs';
import path from 'node:path';
import matter from 'gray-matter';

// Define the path to the content directory
// In Docker, this is mapped to the volume where n8n writes
const INTEL_DIR = path.join(process.cwd(), 'src/content/intelligence');

export interface IntelPost {
    slug: string;
    data: {
        title: string;
        pubDate: Date;
        severity: string;
        sector: string;
        tags?: string[];
        draft?: boolean;
        [key: string]: any;
    };
    content: string;
}

export function getLiveIntelligence(): IntelPost[] {
    if (!fs.existsSync(INTEL_DIR)) return [];

    const files = fs.readdirSync(INTEL_DIR).filter(f => f.endsWith('.md'));
    
    const posts = files.map(fileName => {
        const filePath = path.join(INTEL_DIR, fileName);
        const fileContent = fs.readFileSync(filePath, 'utf-8');
        const { data, content } = matter(fileContent);

        return {
            slug: fileName.replace('.md', ''),
            data: {
                ...data,
                pubDate: new Date(data.pubDate), // Ensure Date object
                severity: data.severity || 'Low',
                sector: data.sector || 'General'
            },
            content
        } as IntelPost;
    });

    // Sort by Date Descending
    return posts.sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf());
}

export function getLiveIntelBySlug(slug: string): IntelPost | null {
    const filePath = path.join(INTEL_DIR, `${slug}.md`);
    
    if (!fs.existsSync(filePath)) return null;

    const fileContent = fs.readFileSync(filePath, 'utf-8');
    const { data, content } = matter(fileContent);

    return {
        slug,
        data: {
            ...data,
            pubDate: new Date(data.pubDate),
            severity: data.severity || 'Low',
            sector: data.sector || 'General'
        },
        content
    } as IntelPost;
}
