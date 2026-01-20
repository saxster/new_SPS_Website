import DOMPurify from 'dompurify';

/**
 * Sanitizes and formats a message with markdown-like syntax.
 *
 * Applies the following transformations:
 * 1. Converts markdown-like syntax to HTML (bold, italic, code, newlines)
 * 2. Sanitizes the result with DOMPurify to prevent XSS attacks
 *
 * @param text - The raw message text
 * @returns Sanitized HTML string safe for dangerouslySetInnerHTML
 */
export function sanitizeAndFormatMessage(text: string): string {
  // First apply markdown-like formatting
  const formatted = text
    .replace(/\n/g, '<br/>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>');

  // Then sanitize to remove any malicious content
  return DOMPurify.sanitize(formatted, {
    ALLOWED_TAGS: ['br', 'strong', 'em', 'code', 'div', 'span', 'p'],
    ALLOWED_ATTR: [],
  });
}
