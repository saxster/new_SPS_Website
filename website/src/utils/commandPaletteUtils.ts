/**
 * Command Palette Utilities
 * Pure functions for query parsing and filtering
 */

export interface ParsedQuery {
  type: 'action' | 'search';
  action?: string;
  filters: {
    in?: string[];
    sector?: string[];
    tag?: string[];
    severity?: string[];
    type?: string[];
  };
  searchTerm: string;
}

export interface SearchIndexItem {
  title: string;
  type: 'PAGE' | 'TOOL' | 'INTEL' | 'ARTICLE' | 'SECTOR' | 'CASE' | 'QNA';
  url: string;
  description: string;
  sector?: string;
  tags?: string[];
  severity?: string;
  category?: string;
  pubDate?: string;
}

// Valid filter names
const VALID_FILTERS = ['in', 'sector', 'tag', 'severity', 'type'] as const;
type FilterName = typeof VALID_FILTERS[number];

// Valid action commands
export const VALID_ACTIONS = ['subscribe', 'contact', 'calculator', 'risk', 'ask', 'help'] as const;
export type ActionName = typeof VALID_ACTIONS[number];

// Type mapping for in: filter
const TYPE_MAP: Record<string, SearchIndexItem['type'][]> = {
  'intel': ['INTEL'],
  'blog': ['ARTICLE'],
  'article': ['ARTICLE'],
  'sectors': ['SECTOR'],
  'sector': ['SECTOR'],
  'cases': ['CASE'],
  'case': ['CASE'],
  'qna': ['QNA'],
  'tools': ['TOOL'],
  'tool': ['TOOL'],
  'pages': ['PAGE'],
  'page': ['PAGE'],
};

/**
 * Parse a query string into filters, actions, and search terms
 */
export function parseQuery(input: string): ParsedQuery {
  const trimmed = input.trim();

  // Check for action command
  if (trimmed.startsWith('>')) {
    const action = trimmed.slice(1).trim().toLowerCase();
    return {
      type: 'action',
      action,
      filters: {},
      searchTerm: ''
    };
  }

  // Parse filters and search term
  const filters: ParsedQuery['filters'] = {};
  const searchTermParts: string[] = [];

  // Split by whitespace
  const tokens = trimmed.split(/\s+/);

  for (const token of tokens) {
    // Check if token is a filter (format: name:value)
    const colonIndex = token.indexOf(':');

    if (colonIndex > 0 && colonIndex < token.length - 1) {
      const filterName = token.slice(0, colonIndex).toLowerCase();
      const filterValue = token.slice(colonIndex + 1).toLowerCase();

      if (VALID_FILTERS.includes(filterName as FilterName)) {
        const key = filterName as FilterName;
        if (!filters[key]) {
          filters[key] = [];
        }
        filters[key]!.push(filterValue);
        continue;
      }
    }

    // Not a filter, add to search term
    if (token) {
      searchTermParts.push(token);
    }
  }

  return {
    type: 'search',
    filters,
    searchTerm: searchTermParts.join(' ').trim()
  };
}

/**
 * Filter search results based on parsed query
 */
export function filterResults(items: SearchIndexItem[], query: ParsedQuery): SearchIndexItem[] {
  if (query.type === 'action') {
    return [];
  }

  let results = [...items];

  // Apply in: filter (maps to type)
  if (query.filters.in && query.filters.in.length > 0) {
    const allowedTypes: Set<string> = new Set();
    for (const inValue of query.filters.in) {
      const mappedTypes = TYPE_MAP[inValue];
      if (mappedTypes) {
        mappedTypes.forEach(t => allowedTypes.add(t));
      }
    }
    if (allowedTypes.size > 0) {
      results = results.filter(item => allowedTypes.has(item.type));
    } else {
      // Invalid filter values, return empty
      results = [];
    }
  }

  // Apply sector: filter (OR logic)
  if (query.filters.sector && query.filters.sector.length > 0) {
    const sectors = new Set(query.filters.sector);
    results = results.filter(item => item.sector && sectors.has(item.sector.toLowerCase()));
  }

  // Apply tag: filter (OR logic - match any tag)
  if (query.filters.tag && query.filters.tag.length > 0) {
    const filterTags = new Set(query.filters.tag);
    results = results.filter(item =>
      item.tags?.some(tag => filterTags.has(tag.toLowerCase()))
    );
  }

  // Apply severity: filter (OR logic)
  if (query.filters.severity && query.filters.severity.length > 0) {
    const severities = new Set(query.filters.severity);
    results = results.filter(item => item.severity && severities.has(item.severity.toLowerCase()));
  }

  // Apply type: filter (OR logic)
  if (query.filters.type && query.filters.type.length > 0) {
    const types = new Set(query.filters.type.map(t => t.toUpperCase()));
    results = results.filter(item => types.has(item.type));
  }

  // Apply search term
  if (query.searchTerm) {
    const term = query.searchTerm.toLowerCase();
    results = results.filter(item =>
      item.title.toLowerCase().includes(term) ||
      item.description.toLowerCase().includes(term)
    );
  }

  return results;
}

/**
 * Normalize tags to lowercase for consistent filtering
 */
export function normalizeTags(tags?: string[]): string[] {
  return tags?.map(t => t.toLowerCase()) ?? [];
}

/**
 * Group results by type for display
 */
export function groupResultsByType(items: SearchIndexItem[]): Map<string, SearchIndexItem[]> {
  const groups = new Map<string, SearchIndexItem[]>();

  for (const item of items) {
    const existing = groups.get(item.type) || [];
    existing.push(item);
    groups.set(item.type, existing);
  }

  return groups;
}

/**
 * Get filter suggestions based on partial input
 */
export function getFilterSuggestions(partialFilter: string): string[] {
  const suggestions: Record<string, string[]> = {
    'in:': ['intel', 'blog', 'sectors', 'cases', 'qna', 'tools', 'pages'],
    'sector:': ['healthcare', 'finance', 'industrial', 'cyber', 'logistics', 'residential', 'education', 'hospitality', 'jewellery', 'petrol'],
    'tag:': ['compliance', 'legal', 'psara', 'analysis', 'strategy', 'report', 'guide'],
    'severity:': ['critical', 'high', 'medium', 'low'],
    'type:': ['page', 'tool', 'intel', 'article', 'sector', 'case', 'qna'],
  };

  for (const [prefix, values] of Object.entries(suggestions)) {
    if (prefix.startsWith(partialFilter.toLowerCase())) {
      return values.map(v => `${prefix}${v}`);
    }
    if (partialFilter.toLowerCase().startsWith(prefix)) {
      const partial = partialFilter.slice(prefix.length).toLowerCase();
      return values
        .filter(v => v.startsWith(partial))
        .map(v => `${prefix}${v}`);
    }
  }

  return [];
}

/**
 * Action command definitions
 */
export interface ActionCommand {
  name: string;
  label: string;
  description: string;
  icon: string;
}

export const ACTIONS: Record<ActionName, ActionCommand> = {
  subscribe: { name: 'subscribe', label: 'Subscribe', description: 'Open newsletter signup', icon: '📬' },
  contact: { name: 'contact', label: 'Contact', description: 'Navigate to contact page', icon: '📞' },
  calculator: { name: 'calculator', label: 'Compliance Calculator', description: 'Open compliance checker', icon: '📋' },
  risk: { name: 'risk', label: 'Risk Calculator', description: 'Open risk assessment tool', icon: '⚠️' },
  ask: { name: 'ask', label: 'Ask SPS AI', description: 'Open AI expert chat', icon: '🤖' },
  help: { name: 'help', label: 'Help', description: 'Show available commands', icon: '❓' },
};
