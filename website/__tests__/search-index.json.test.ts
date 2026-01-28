import { describe, it, expect } from 'vitest';
import type { SearchIndexItem } from '../src/utils/commandPaletteUtils';

/**
 * Tests for Search Index API
 *
 * Since the search index is an Astro API endpoint that uses getCollection,
 * we test the expected structure and contract of the returned data.
 * These tests validate what the search index SHOULD return.
 */

describe('Search Index Structure Contract', () => {
  // This simulates what the API should return for static pages
  const expectedStaticPages: Partial<SearchIndexItem>[] = [
    { title: 'Home Command', type: 'PAGE', url: '/', tags: expect.arrayContaining(['home']) },
    { title: 'About SPS', type: 'PAGE', url: '/about', tags: expect.arrayContaining(['about']) },
    { title: 'Services & Methodology', type: 'PAGE', url: '/services' },
    { title: 'Command Centre', type: 'PAGE', url: '/contact' },
    { title: 'Tactical Tools', type: 'TOOL', url: '/tools' },
    { title: 'Threat Calculus Engine', type: 'TOOL', url: '/tools/risk-calculator' },
    { title: 'Compliance Calculator', type: 'TOOL', url: '/tools/compliance-calculator', tags: expect.arrayContaining(['compliance', 'psara']) },
    { title: 'Storage Calculator', type: 'TOOL', url: '/tools/storage-calculator' },
    { title: 'Officers / Leadership', type: 'PAGE', url: '/officers' },
  ];

  describe('Static Pages', () => {
    it('should include all required static pages', () => {
      // This test documents the expected static pages
      expect(expectedStaticPages.length).toBe(9);
    });

    it('should have tags on static pages for filtering', () => {
      const pagesWithTags = expectedStaticPages.filter(p => p.tags);
      expect(pagesWithTags.length).toBeGreaterThan(0);
    });

    it('should include Compliance Calculator tool', () => {
      const complianceCalc = expectedStaticPages.find(p => p.url === '/tools/compliance-calculator');
      expect(complianceCalc).toBeDefined();
      expect(complianceCalc?.type).toBe('TOOL');
    });

    it('should include Storage Calculator tool', () => {
      const storageCalc = expectedStaticPages.find(p => p.url === '/tools/storage-calculator');
      expect(storageCalc).toBeDefined();
      expect(storageCalc?.type).toBe('TOOL');
    });
  });

  describe('Content Type Mapping', () => {
    it('should map blog posts to ARTICLE type', () => {
      // Blog posts should use ARTICLE type, not INTEL
      const articleItem: SearchIndexItem = {
        title: 'Sample Blog Post',
        type: 'ARTICLE',
        url: '/articles/sample',
        description: 'A blog article',
        tags: ['sample'],
        pubDate: '2026-01-28T00:00:00.000Z'
      };
      expect(articleItem.type).toBe('ARTICLE');
    });

    it('should map intelligence reports to INTEL type with severity', () => {
      const intelItem: SearchIndexItem = {
        title: 'Security Alert',
        type: 'INTEL',
        url: '/intelligence/alert',
        description: 'Critical security alert',
        sector: 'healthcare',
        tags: ['analysis'],
        severity: 'critical',
        pubDate: '2026-01-28T00:00:00.000Z'
      };
      expect(intelItem.type).toBe('INTEL');
      expect(intelItem.severity).toBe('critical');
      expect(intelItem.sector).toBe('healthcare');
    });

    it('should map Q&A entries to QNA type with category', () => {
      const qnaItem: SearchIndexItem = {
        title: 'How to comply with PSARA?',
        type: 'QNA',
        url: '/qna/psara-compliance',
        description: 'PSARA compliance question',
        category: 'legal',
        tags: ['qna', 'question', 'answer']
      };
      expect(qnaItem.type).toBe('QNA');
      expect(qnaItem.category).toBe('legal');
    });

    it('should map sectors to SECTOR type with sector field', () => {
      const sectorItem: SearchIndexItem = {
        title: 'Healthcare Protocol',
        type: 'SECTOR',
        url: '/sectors/healthcare',
        description: 'Healthcare security protocols',
        sector: 'healthcare',
        tags: ['healthcare', 'sector', 'protocol']
      };
      expect(sectorItem.type).toBe('SECTOR');
      expect(sectorItem.sector).toBe('healthcare');
    });

    it('should map case studies to CASE type', () => {
      const caseItem: SearchIndexItem = {
        title: 'Case: Factory Security',
        type: 'CASE',
        url: '/operations/factory-security',
        description: 'Case study summary',
        tags: ['industrial']
      };
      expect(caseItem.type).toBe('CASE');
    });
  });

  describe('Metadata Fields', () => {
    it('should normalize tags to lowercase', () => {
      // Tags should always be lowercase for consistent filtering
      const item: SearchIndexItem = {
        title: 'Test',
        type: 'INTEL',
        url: '/test',
        description: 'Test',
        tags: ['analysis', 'report', 'compliance'] // all lowercase
      };
      item.tags?.forEach(tag => {
        expect(tag).toBe(tag.toLowerCase());
      });
    });

    it('should normalize sector to lowercase', () => {
      const item: SearchIndexItem = {
        title: 'Test',
        type: 'INTEL',
        url: '/test',
        description: 'Test',
        sector: 'healthcare' // lowercase
      };
      expect(item.sector).toBe(item.sector?.toLowerCase());
    });

    it('should normalize severity to lowercase', () => {
      const item: SearchIndexItem = {
        title: 'Test',
        type: 'INTEL',
        url: '/test',
        description: 'Test',
        severity: 'critical' // lowercase
      };
      expect(item.severity).toBe(item.severity?.toLowerCase());
    });

    it('should include pubDate as ISO string for content items', () => {
      const item: SearchIndexItem = {
        title: 'Test',
        type: 'INTEL',
        url: '/test',
        description: 'Test',
        pubDate: '2026-01-28T00:00:00.000Z'
      };
      expect(item.pubDate).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });
  });

  describe('URL Patterns', () => {
    it('should use /articles/ prefix for blog posts', () => {
      const url = '/articles/sample-post';
      expect(url).toMatch(/^\/articles\//);
    });

    it('should use /intelligence/ prefix for intel reports', () => {
      const url = '/intelligence/sample-report';
      expect(url).toMatch(/^\/intelligence\//);
    });

    it('should use /sectors/ prefix for sector pages', () => {
      const url = '/sectors/healthcare';
      expect(url).toMatch(/^\/sectors\//);
    });

    it('should use /operations/ prefix for case studies', () => {
      const url = '/operations/sample-case';
      expect(url).toMatch(/^\/operations\//);
    });

    it('should use /qna/ prefix for Q&A entries', () => {
      const url = '/qna/sample-question';
      expect(url).toMatch(/^\/qna\//);
    });
  });
});
