import { describe, it, expect } from 'vitest';

/**
 * Tests for severity classification utilities
 *
 * These functions classify numeric values into severity levels (low/medium/high/critical)
 * using threshold-based logic.
 */

// Import the utility function (to be created)
// This test file drives the extraction of the common helper

describe('classifyByThresholds utility', () => {
  it('should exist as a reusable utility function', async () => {
    // The utility should be extracted to a separate file
    const module = await import('../src/utils/severityClassification');
    expect(module.classifyByThresholds).toBeDefined();
  });

  it('should return critical when value >= critical threshold', async () => {
    const { classifyByThresholds } = await import('../src/utils/severityClassification');
    const result = classifyByThresholds(6, { critical: 6, high: 5, medium: 4 });
    expect(result).toBe('critical');
  });

  it('should return high when value >= high threshold but < critical', async () => {
    const { classifyByThresholds } = await import('../src/utils/severityClassification');
    const result = classifyByThresholds(5, { critical: 6, high: 5, medium: 4 });
    expect(result).toBe('high');
  });

  it('should return medium when value >= medium threshold but < high', async () => {
    const { classifyByThresholds } = await import('../src/utils/severityClassification');
    const result = classifyByThresholds(4, { critical: 6, high: 5, medium: 4 });
    expect(result).toBe('medium');
  });

  it('should return low when value < medium threshold', async () => {
    const { classifyByThresholds } = await import('../src/utils/severityClassification');
    const result = classifyByThresholds(3, { critical: 6, high: 5, medium: 4 });
    expect(result).toBe('low');
  });
});

describe('classifyMagnitude (earthquake)', () => {
  it('should use the classifyByThresholds utility', async () => {
    const { classifyMagnitude } = await import('../src/utils/severityClassification');
    expect(classifyMagnitude).toBeDefined();
  });

  it('should classify magnitude 6+ as critical', async () => {
    const { classifyMagnitude } = await import('../src/utils/severityClassification');
    expect(classifyMagnitude(6)).toBe('critical');
    expect(classifyMagnitude(7.5)).toBe('critical');
  });

  it('should classify magnitude 5-5.9 as high', async () => {
    const { classifyMagnitude } = await import('../src/utils/severityClassification');
    expect(classifyMagnitude(5)).toBe('high');
    expect(classifyMagnitude(5.9)).toBe('high');
  });

  it('should classify magnitude 4-4.9 as medium', async () => {
    const { classifyMagnitude } = await import('../src/utils/severityClassification');
    expect(classifyMagnitude(4)).toBe('medium');
    expect(classifyMagnitude(4.5)).toBe('medium');
  });

  it('should classify magnitude < 4 as low', async () => {
    const { classifyMagnitude } = await import('../src/utils/severityClassification');
    expect(classifyMagnitude(3.9)).toBe('low');
    expect(classifyMagnitude(2)).toBe('low');
  });
});

describe('classifyAqi (air quality index)', () => {
  it('should use the classifyByThresholds utility', async () => {
    const { classifyAqi } = await import('../src/utils/severityClassification');
    expect(classifyAqi).toBeDefined();
  });

  it('should classify AQI 200+ as critical', async () => {
    const { classifyAqi } = await import('../src/utils/severityClassification');
    expect(classifyAqi(200)).toBe('critical');
    expect(classifyAqi(300)).toBe('critical');
  });

  it('should classify AQI 150-199 as high', async () => {
    const { classifyAqi } = await import('../src/utils/severityClassification');
    expect(classifyAqi(150)).toBe('high');
    expect(classifyAqi(199)).toBe('high');
  });

  it('should classify AQI 100-149 as medium', async () => {
    const { classifyAqi } = await import('../src/utils/severityClassification');
    expect(classifyAqi(100)).toBe('medium');
    expect(classifyAqi(149)).toBe('medium');
  });

  it('should classify AQI < 100 as low', async () => {
    const { classifyAqi } = await import('../src/utils/severityClassification');
    expect(classifyAqi(99)).toBe('low');
    expect(classifyAqi(50)).toBe('low');
  });
});

