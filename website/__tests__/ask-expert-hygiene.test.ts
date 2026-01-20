import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Code Hygiene Tests for ask-expert.ts
 *
 * These tests ensure no dead code exists in the file:
 * - No unused imports
 * - No unused constants
 * - No commented-out code blocks
 */

describe('ask-expert.ts code hygiene', () => {
  const filePath = path.join(__dirname, '../src/pages/api/ask-expert.ts');
  const content = fs.readFileSync(filePath, 'utf-8');

  it('should not import fetchWithTimeout if not used', () => {
    const importLine = content.match(/import\s*\{[^}]*fetchWithTimeout[^}]*\}/);
    if (importLine) {
      // Count occurrences - should be more than 1 if actually used (import + usage)
      const occurrences = (content.match(/fetchWithTimeout/g) || []).length;
      expect(occurrences).toBeGreaterThan(1);
    }
  });

  it('should not have unused SYSTEM_PROMPT constant', () => {
    const hasDeclaration = content.includes('const SYSTEM_PROMPT');
    if (hasDeclaration) {
      // Count occurrences - should be more than 1 if actually used (declaration + usage)
      const occurrences = (content.match(/SYSTEM_PROMPT/g) || []).length;
      expect(occurrences).toBeGreaterThan(1);
    }
  });

  it('should not have unused API_TIMEOUT_MS constant', () => {
    const hasDeclaration = content.includes('const API_TIMEOUT_MS');
    if (hasDeclaration) {
      // Count occurrences - should be more than 1 if actually used
      const occurrences = (content.match(/API_TIMEOUT_MS/g) || []).length;
      expect(occurrences).toBeGreaterThan(1);
    }
  });

  it('should not have commented-out API key code', () => {
    // Check for commented import.meta.env API key patterns
    const hasCommentedApiKey = /\/\/\s*const\s+apiKey\s*=\s*import\.meta\.env/.test(content);
    expect(hasCommentedApiKey).toBe(false);
  });

  it('should not have placeholder comments about removed functions', () => {
    // Check for comments indicating removed code
    const hasRemovedComment = /\/\/.*REMOVED|COMMENTED OUT/i.test(content);
    expect(hasRemovedComment).toBe(false);
  });
});
