import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Code hygiene tests for HybridIntelConsole component
 *
 * Verifies the component uses extracted utility functions
 * instead of inline definitions.
 */

describe('HybridIntelConsole code hygiene', () => {
  const filePath = path.join(__dirname, '../src/components/intelligence/HybridIntelConsole.tsx');
  const content = fs.readFileSync(filePath, 'utf-8');

  it('should import classifyMagnitude from utility module', () => {
    expect(content).toContain("from '../../utils/severityClassification'");
  });

  it('should not have inline classifyMagnitude definition', () => {
    // Should NOT have inline definition with function body
    const inlineDefinition = /const classifyMagnitude\s*=\s*\(mag:\s*number\)\s*:\s*Severity\s*=>\s*\{/;
    expect(inlineDefinition.test(content)).toBe(false);
  });

  it('should import classifyAqi from utility module', () => {
    expect(content).toContain('classifyAqi');
    expect(content).toContain("from '../../utils/severityClassification'");
  });

  it('should not have inline classifyAqi definition', () => {
    // Should NOT have inline definition with function body
    const inlineDefinition = /const classifyAqi\s*=\s*\(aqi:\s*number\)\s*:\s*Severity\s*=>\s*\{/;
    expect(inlineDefinition.test(content)).toBe(false);
  });
});
