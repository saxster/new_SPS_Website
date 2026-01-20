import { describe, it, expect } from 'vitest';

/**
 * Tests for XSS Prevention via HTML Sanitization
 *
 * These tests verify that the sanitizeAndFormatMessage function:
 * 1. Strips malicious script tags
 * 2. Removes event handlers (onclick, onerror, etc.)
 * 3. Blocks javascript: URLs
 * 4. Preserves safe markdown-like formatting
 */

describe('sanitizeAndFormatMessage', () => {
  it('should strip script tags from messages', async () => {
    const { sanitizeAndFormatMessage } = await import('../src/utils/sanitize');

    const maliciousInput = '<script>alert("xss")</script>Hello';
    const result = sanitizeAndFormatMessage(maliciousInput);

    expect(result).not.toContain('<script>');
    expect(result).not.toContain('alert');
    expect(result).toContain('Hello');
  });

  it('should strip onclick handlers from messages', async () => {
    const { sanitizeAndFormatMessage } = await import('../src/utils/sanitize');

    const maliciousInput = '<div onclick="alert(1)">Click me</div>';
    const result = sanitizeAndFormatMessage(maliciousInput);

    expect(result).not.toContain('onclick');
    expect(result).toContain('Click me');
  });

  it('should strip javascript: URLs from messages', async () => {
    const { sanitizeAndFormatMessage } = await import('../src/utils/sanitize');

    const maliciousInput = '<a href="javascript:alert(1)">Link</a>';
    const result = sanitizeAndFormatMessage(maliciousInput);

    expect(result).not.toContain('javascript:');
  });

  it('should preserve safe markdown-like formatting', async () => {
    const { sanitizeAndFormatMessage } = await import('../src/utils/sanitize');

    const safeInput = '**bold** and *italic* and `code`';
    const result = sanitizeAndFormatMessage(safeInput);

    expect(result).toContain('<strong>bold</strong>');
    expect(result).toContain('<em>italic</em>');
    expect(result).toContain('<code>code</code>');
  });

  it('should convert newlines to br tags', async () => {
    const { sanitizeAndFormatMessage } = await import('../src/utils/sanitize');

    const input = 'Line 1\nLine 2';
    const result = sanitizeAndFormatMessage(input);

    // DOMPurify normalizes <br/> to <br>
    expect(result).toContain('<br>');
  });
});
