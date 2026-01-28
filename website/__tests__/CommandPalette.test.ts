import { describe, it, expect } from 'vitest';
import {
  parseQuery,
  filterResults,
  normalizeTags,
  type ParsedQuery,
  type SearchIndexItem
} from '../src/utils/commandPaletteUtils';

/**
 * Tests for Command Palette Enhanced Features
 *
 * Tests cover:
 * 1. Query parsing - extracting filters, actions, and search terms
 * 2. Filter logic - applying in:, sector:, tag:, severity: filters
 * 3. Action commands - parsing >action syntax
 * 4. Search index structure - verifying metadata fields
 */

describe('Query Parser', () => {
  describe('Action Commands', () => {
    it('should detect action command when query starts with >', () => {
      const result = parseQuery('>subscribe');
      expect(result.type).toBe('action');
      expect(result.action).toBe('subscribe');
    });

    it('should parse action with extra whitespace', () => {
      const result = parseQuery('>  contact  ');
      expect(result.type).toBe('action');
      expect(result.action).toBe('contact');
    });

    it('should recognize all valid actions', () => {
      const actions = ['subscribe', 'contact', 'calculator', 'risk', 'ask', 'help'];
      for (const action of actions) {
        const result = parseQuery(`>${action}`);
        expect(result.type).toBe('action');
        expect(result.action).toBe(action);
      }
    });
  });

  describe('Filter Parsing', () => {
    it('should parse in: filter', () => {
      const result = parseQuery('in:intel ransomware');
      expect(result.type).toBe('search');
      expect(result.filters.in).toContain('intel');
      expect(result.searchTerm).toBe('ransomware');
    });

    it('should parse sector: filter', () => {
      const result = parseQuery('sector:healthcare compliance');
      expect(result.type).toBe('search');
      expect(result.filters.sector).toContain('healthcare');
      expect(result.searchTerm).toBe('compliance');
    });

    it('should parse tag: filter', () => {
      const result = parseQuery('tag:legal psara requirements');
      expect(result.type).toBe('search');
      expect(result.filters.tag).toContain('legal');
      expect(result.searchTerm).toBe('psara requirements');
    });

    it('should parse severity: filter', () => {
      const result = parseQuery('severity:critical alerts');
      expect(result.type).toBe('search');
      expect(result.filters.severity).toContain('critical');
      expect(result.searchTerm).toBe('alerts');
    });

    it('should parse multiple different filters', () => {
      const result = parseQuery('in:intel sector:healthcare data breach');
      expect(result.type).toBe('search');
      expect(result.filters.in).toContain('intel');
      expect(result.filters.sector).toContain('healthcare');
      expect(result.searchTerm).toBe('data breach');
    });

    it('should handle multiple values for same filter type', () => {
      const result = parseQuery('sector:healthcare sector:finance audit');
      expect(result.type).toBe('search');
      expect(result.filters.sector).toContain('healthcare');
      expect(result.filters.sector).toContain('finance');
      expect(result.searchTerm).toBe('audit');
    });

    it('should ignore invalid filter names', () => {
      const result = parseQuery('invalid:value query');
      expect(result.type).toBe('search');
      expect(result.searchTerm).toBe('invalid:value query');
    });

    it('should handle filter with no search term', () => {
      const result = parseQuery('in:intel');
      expect(result.type).toBe('search');
      expect(result.filters.in).toContain('intel');
      expect(result.searchTerm).toBe('');
    });

    it('should only parse colon as filter when before first space in token', () => {
      const result = parseQuery('time: 10:30 meeting');
      expect(result.type).toBe('search');
      // "time:" is not a valid filter, so should be part of search term
      expect(result.searchTerm).toContain('time:');
    });
  });

  describe('Plain Search', () => {
    it('should return search type with no filters for plain query', () => {
      const result = parseQuery('ransomware attack');
      expect(result.type).toBe('search');
      expect(result.filters.in).toBeUndefined();
      expect(result.filters.sector).toBeUndefined();
      expect(result.searchTerm).toBe('ransomware attack');
    });

    it('should handle empty query', () => {
      const result = parseQuery('');
      expect(result.type).toBe('search');
      expect(result.searchTerm).toBe('');
    });

    it('should trim whitespace from search term', () => {
      const result = parseQuery('  ransomware  ');
      expect(result.searchTerm).toBe('ransomware');
    });
  });
});

describe('Filter Logic', () => {
  const mockIndex: SearchIndexItem[] = [
    { title: 'Healthcare Data Breach', type: 'INTEL', url: '/intel/1', description: 'Analysis of breach', sector: 'healthcare', tags: ['analysis', 'breach'], severity: 'critical' },
    { title: 'Finance Security Guide', type: 'ARTICLE', url: '/articles/1', description: 'Security for banks', sector: 'finance', tags: ['guide', 'compliance'] },
    { title: 'Industrial Fire Report', type: 'INTEL', url: '/intel/2', description: 'Factory fire analysis', sector: 'industrial', tags: ['fire', 'analysis'], severity: 'high' },
    { title: 'PSARA Compliance FAQ', type: 'QNA', url: '/qna/1', description: 'PSARA questions', tags: ['psara', 'legal', 'compliance'], category: 'legal' },
    { title: 'Risk Calculator', type: 'TOOL', url: '/tools/risk', description: 'Calculate risk', tags: ['calculator', 'risk'] },
    { title: 'Healthcare Protocol', type: 'SECTOR', url: '/sectors/healthcare', description: 'Healthcare security', sector: 'healthcare', tags: ['healthcare', 'protocol'] },
  ];

  describe('in: filter', () => {
    it('should filter by content type INTEL', () => {
      const query: ParsedQuery = { type: 'search', filters: { in: ['intel'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.type === 'INTEL')).toBe(true);
      expect(results.length).toBe(2);
    });

    it('should filter by content type ARTICLE', () => {
      const query: ParsedQuery = { type: 'search', filters: { in: ['article'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.type === 'ARTICLE')).toBe(true);
    });

    it('should filter by content type QNA', () => {
      const query: ParsedQuery = { type: 'search', filters: { in: ['qna'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.type === 'QNA')).toBe(true);
    });

    it('should apply OR logic for multiple in: values', () => {
      const query: ParsedQuery = { type: 'search', filters: { in: ['intel', 'article'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.type === 'INTEL' || r.type === 'ARTICLE')).toBe(true);
      expect(results.length).toBe(3);
    });
  });

  describe('sector: filter', () => {
    it('should filter by sector', () => {
      const query: ParsedQuery = { type: 'search', filters: { sector: ['healthcare'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.sector === 'healthcare')).toBe(true);
      expect(results.length).toBe(2);
    });

    it('should apply OR logic for multiple sectors', () => {
      const query: ParsedQuery = { type: 'search', filters: { sector: ['healthcare', 'finance'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.sector === 'healthcare' || r.sector === 'finance')).toBe(true);
      expect(results.length).toBe(3);
    });
  });

  describe('tag: filter', () => {
    it('should filter by tag', () => {
      const query: ParsedQuery = { type: 'search', filters: { tag: ['compliance'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.tags?.includes('compliance'))).toBe(true);
      expect(results.length).toBe(2);
    });

    it('should apply OR logic for multiple tags', () => {
      const query: ParsedQuery = { type: 'search', filters: { tag: ['fire', 'breach'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.tags?.includes('fire') || r.tags?.includes('breach'))).toBe(true);
      expect(results.length).toBe(2);
    });
  });

  describe('severity: filter', () => {
    it('should filter by critical severity', () => {
      const query: ParsedQuery = { type: 'search', filters: { severity: ['critical'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.severity === 'critical')).toBe(true);
      expect(results.length).toBe(1);
    });

    it('should apply OR logic for multiple severities', () => {
      const query: ParsedQuery = { type: 'search', filters: { severity: ['critical', 'high'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.severity === 'critical' || r.severity === 'high')).toBe(true);
      expect(results.length).toBe(2);
    });
  });

  describe('Combined Filters', () => {
    it('should apply AND logic between different filter types', () => {
      const query: ParsedQuery = { type: 'search', filters: { sector: ['healthcare'], in: ['intel'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.every(r => r.sector === 'healthcare' && r.type === 'INTEL')).toBe(true);
      expect(results.length).toBe(1);
    });

    it('should combine filters with search term', () => {
      const query: ParsedQuery = { type: 'search', filters: { in: ['intel'] }, searchTerm: 'fire' };
      const results = filterResults(mockIndex, query);
      expect(results.length).toBe(1);
      expect(results[0].title).toContain('Fire');
    });
  });

  describe('Edge Cases', () => {
    it('should return all items when no filters applied', () => {
      const query: ParsedQuery = { type: 'search', filters: {}, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.length).toBe(mockIndex.length);
    });

    it('should return empty array when no matches', () => {
      const query: ParsedQuery = { type: 'search', filters: { sector: ['nonexistent'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.length).toBe(0);
    });

    it('should ignore invalid filter values gracefully', () => {
      const query: ParsedQuery = { type: 'search', filters: { in: ['invalid_type'] }, searchTerm: '' };
      const results = filterResults(mockIndex, query);
      expect(results.length).toBe(0);
    });
  });
});

describe('Search Index Structure', () => {
  describe('normalizeTags', () => {
    it('should convert tags to lowercase', () => {
      const result = normalizeTags(['Analysis', 'REPORT', 'Compliance']);
      expect(result).toEqual(['analysis', 'report', 'compliance']);
    });

    it('should return empty array for undefined', () => {
      const result = normalizeTags(undefined);
      expect(result).toEqual([]);
    });

    it('should return empty array for empty array', () => {
      const result = normalizeTags([]);
      expect(result).toEqual([]);
    });
  });

  describe('SearchIndexItem shape', () => {
    it('should validate required fields', () => {
      const item: SearchIndexItem = {
        title: 'Test',
        type: 'INTEL',
        url: '/test',
        description: 'Test description'
      };
      expect(item.title).toBeDefined();
      expect(item.type).toBeDefined();
      expect(item.url).toBeDefined();
      expect(item.description).toBeDefined();
    });

    it('should allow optional metadata fields', () => {
      const item: SearchIndexItem = {
        title: 'Test',
        type: 'INTEL',
        url: '/test',
        description: 'Test description',
        sector: 'healthcare',
        tags: ['tag1', 'tag2'],
        severity: 'critical',
        category: 'legal',
        pubDate: '2026-01-28'
      };
      expect(item.sector).toBe('healthcare');
      expect(item.tags).toContain('tag1');
      expect(item.severity).toBe('critical');
      expect(item.category).toBe('legal');
      expect(item.pubDate).toBe('2026-01-28');
    });
  });
});
