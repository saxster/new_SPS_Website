/**
 * Reading Time Utility
 * 
 * Calculates estimated reading time based on word count.
 * Uses 200 WPM average for technical/security content.
 */

/**
 * Calculate reading time in minutes from content string
 * @param content - The text content to analyze
 * @param wordsPerMinute - Reading speed (default: 200 WPM for technical content)
 * @returns Reading time in minutes, minimum 1
 */
export function getReadingTime(content: string, wordsPerMinute = 200): number {
  // Remove markdown formatting for more accurate word count
  const plainText = content
    .replace(/```[\s\S]*?```/g, '') // Remove code blocks
    .replace(/`[^`]*`/g, '')         // Remove inline code
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // Convert links to text
    .replace(/[#*_~]/g, '')          // Remove markdown formatting
    .replace(/\n+/g, ' ')            // Normalize whitespace
    .trim();
  
  const words = plainText.split(/\s+/).filter(word => word.length > 0).length;
  return Math.max(1, Math.ceil(words / wordsPerMinute));
}

/**
 * Format reading time for display
 * @param minutes - Reading time in minutes
 * @returns Formatted string like "5 min read"
 */
export function formatReadingTime(minutes: number): string {
  return `${minutes} min read`;
}
