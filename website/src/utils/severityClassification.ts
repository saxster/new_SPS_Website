/**
 * Severity Classification Utilities
 *
 * Provides threshold-based classification of numeric values into severity levels.
 * Used for earthquake magnitude, air quality index, and other metrics.
 */

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export interface SeverityThresholds {
  critical: number;
  high: number;
  medium: number;
}

/**
 * Classify a numeric value into a severity level based on thresholds.
 *
 * @param value - The numeric value to classify
 * @param thresholds - Object with critical, high, and medium threshold values
 * @returns The severity level: 'critical', 'high', 'medium', or 'low'
 */
export function classifyByThresholds(
  value: number,
  thresholds: SeverityThresholds
): Severity {
  if (value >= thresholds.critical) return 'critical';
  if (value >= thresholds.high) return 'high';
  if (value >= thresholds.medium) return 'medium';
  return 'low';
}

// Pre-configured classifiers for common use cases

const EARTHQUAKE_THRESHOLDS: SeverityThresholds = {
  critical: 6,
  high: 5,
  medium: 4,
};

const AQI_THRESHOLDS: SeverityThresholds = {
  critical: 200,
  high: 150,
  medium: 100,
};

/**
 * Classify earthquake magnitude into severity.
 * - Critical: M6.0+
 * - High: M5.0-5.9
 * - Medium: M4.0-4.9
 * - Low: < M4.0
 */
export const classifyMagnitude = (mag: number): Severity =>
  classifyByThresholds(mag, EARTHQUAKE_THRESHOLDS);

/**
 * Classify Air Quality Index (US AQI) into severity.
 * - Critical: 200+ (Very Unhealthy)
 * - High: 150-199 (Unhealthy)
 * - Medium: 100-149 (Unhealthy for Sensitive Groups)
 * - Low: < 100 (Good/Moderate)
 */
export const classifyAqi = (aqi: number): Severity =>
  classifyByThresholds(aqi, AQI_THRESHOLDS);
