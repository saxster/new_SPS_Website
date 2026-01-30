import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

/**
 * Tests for health-checks.ts
 *
 * Health checks verify system status for monitoring:
 * - Filesystem access to content directories
 * - Memory usage below thresholds
 * - Content availability
 * - Backend API connectivity
 */

// These will be imported once implementation exists
// import {
//   checkFilesystem,
//   checkMemory,
//   checkContentCount,
//   checkBackend,
//   runHealthChecks,
//   type HealthCheckResult,
//   type HealthReport,
// } from '../src/lib/health-checks';

describe('health-checks', () => {
  describe('checkFilesystem', () => {
    it('returns healthy when content directories exist and are readable', async () => {
      // Import will work once implementation exists
      const { checkFilesystem } = await import('../src/lib/health-checks');

      const result = await checkFilesystem();

      expect(result).toMatchObject({
        name: 'filesystem',
        healthy: expect.any(Boolean),
        message: expect.any(String),
      });
      // In the actual project, these directories exist
      expect(result.healthy).toBe(true);
      expect(result.message).toContain('accessible');
    });

    it('returns result with name filesystem and message about directory status', async () => {
      const { checkFilesystem } = await import('../src/lib/health-checks');

      // Test the actual structure - we can't mock ESM fs exports
      const result = await checkFilesystem();

      expect(result.name).toBe('filesystem');
      expect(typeof result.healthy).toBe('boolean');
      expect(typeof result.message).toBe('string');
      // The message should describe the directory status
      expect(result.message.length).toBeGreaterThan(0);
    });
  });

  describe('checkMemory', () => {
    it('returns healthy when memory usage is below 90%', async () => {
      const { checkMemory } = await import('../src/lib/health-checks');

      const result = checkMemory();

      expect(result).toMatchObject({
        name: 'memory',
        healthy: expect.any(Boolean),
        message: expect.any(String),
        value: expect.any(Number),
        threshold: 90,
      });
      // Normal test environment should have healthy memory
      expect(result.healthy).toBe(true);
    });

    it('returns unhealthy when memory usage exceeds 90%', async () => {
      const { checkMemory, MEMORY_THRESHOLD_PERCENT } = await import('../src/lib/health-checks');

      // Mock process.memoryUsage to simulate high memory
      const originalMemoryUsage = process.memoryUsage;
      vi.spyOn(process, 'memoryUsage').mockReturnValue({
        heapUsed: 950 * 1024 * 1024, // 950MB used
        heapTotal: 1000 * 1024 * 1024, // 1000MB total (95% usage)
        external: 0,
        arrayBuffers: 0,
        rss: 1000 * 1024 * 1024,
      });

      const result = checkMemory();

      expect(result.healthy).toBe(false);
      expect(result.message).toContain('HIGH');
      expect(result.value).toBeGreaterThan(90);

      vi.restoreAllMocks();
    });

    it('includes percentage value in result', async () => {
      const { checkMemory } = await import('../src/lib/health-checks');

      const result = checkMemory();

      expect(typeof result.value).toBe('number');
      expect(result.value).toBeGreaterThanOrEqual(0);
      expect(result.value).toBeLessThanOrEqual(100);
    });
  });

  describe('checkContentCount', () => {
    it('returns healthy when content files exist', async () => {
      const { checkContentCount } = await import('../src/lib/health-checks');

      const result = await checkContentCount();

      expect(result).toMatchObject({
        name: 'content',
        healthy: expect.any(Boolean),
        message: expect.any(String),
        value: expect.any(Number),
        threshold: expect.any(Number),
      });
      // Project has content files
      expect(result.healthy).toBe(true);
      expect(result.value).toBeGreaterThan(0);
    });

    it('includes threshold in result for content minimum', async () => {
      const { checkContentCount, CONTENT_MIN_COUNT } = await import('../src/lib/health-checks');

      const result = await checkContentCount();

      expect(result.name).toBe('content');
      expect(result.threshold).toBe(CONTENT_MIN_COUNT);
      expect(typeof result.value).toBe('number');
    });

    it('counts both intelligence and blog content', async () => {
      const { checkContentCount } = await import('../src/lib/health-checks');

      const result = await checkContentCount();

      // Message should mention both types
      expect(result.message).toMatch(/intelligence.*blog|blog.*intelligence/i);
    });
  });

  describe('checkBackend', () => {
    it('returns healthy when backend responds with 200', async () => {
      const { checkBackend } = await import('../src/lib/health-checks');

      // Mock successful fetch
      vi.spyOn(global, 'fetch').mockResolvedValue(
        new Response(JSON.stringify({ status: 'ok' }), { status: 200 })
      );

      const result = await checkBackend();

      expect(result).toMatchObject({
        name: 'backend',
        healthy: true,
        message: expect.stringContaining('reachable'),
      });

      vi.restoreAllMocks();
    });

    it('returns unhealthy when backend is unreachable', async () => {
      const { checkBackend } = await import('../src/lib/health-checks');

      // Mock failed fetch
      vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Connection refused'));

      const result = await checkBackend();

      expect(result.healthy).toBe(false);
      expect(result.message).toContain('unreachable');

      vi.restoreAllMocks();
    });

    it('returns unhealthy when backend returns non-200 status', async () => {
      const { checkBackend } = await import('../src/lib/health-checks');

      vi.spyOn(global, 'fetch').mockResolvedValue(
        new Response('Internal Server Error', { status: 500 })
      );

      const result = await checkBackend();

      expect(result.healthy).toBe(false);
      expect(result.message).toContain('500');

      vi.restoreAllMocks();
    });

    it('handles timeout gracefully', async () => {
      const { checkBackend } = await import('../src/lib/health-checks');

      // Mock abort error
      vi.spyOn(global, 'fetch').mockRejectedValue(
        Object.assign(new Error('Aborted'), { name: 'AbortError' })
      );

      const result = await checkBackend();

      expect(result.healthy).toBe(false);
      expect(result.message).toContain('timeout');

      vi.restoreAllMocks();
    });
  });

  describe('runHealthChecks', () => {
    beforeEach(() => {
      // Mock backend check to avoid network calls in tests
      vi.spyOn(global, 'fetch').mockResolvedValue(
        new Response(JSON.stringify({ status: 'ok' }), { status: 200 })
      );
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('returns a complete health report', async () => {
      const { runHealthChecks } = await import('../src/lib/health-checks');

      const report = await runHealthChecks();

      expect(report).toMatchObject({
        timestamp: expect.any(String),
        status: expect.stringMatching(/^(healthy|degraded|unhealthy)$/),
        version: expect.any(String),
        uptime: expect.any(Number),
        checks: expect.objectContaining({
          filesystem: expect.any(Object),
          memory: expect.any(Object),
          content: expect.any(Object),
          backend: expect.any(Object),
        }),
        diagnostics: expect.objectContaining({
          memory: expect.any(Object),
          system: expect.any(Object),
        }),
      });
    });

    it('returns healthy status when all critical checks pass', async () => {
      const { runHealthChecks } = await import('../src/lib/health-checks');

      const report = await runHealthChecks();

      // In normal test environment, all should pass
      expect(['healthy', 'degraded']).toContain(report.status);
    });

    it('includes all check results in the report', async () => {
      const { runHealthChecks } = await import('../src/lib/health-checks');

      const report = await runHealthChecks();

      // Verify all checks are present and have required structure
      const checkNames = ['filesystem', 'memory', 'content', 'backend'];
      for (const name of checkNames) {
        expect(report.checks[name]).toBeDefined();
        expect(report.checks[name].name).toBe(name);
        expect(typeof report.checks[name].healthy).toBe('boolean');
        expect(typeof report.checks[name].message).toBe('string');
      }
    });

    it('returns degraded status when only non-critical check fails', async () => {
      const { runHealthChecks } = await import('../src/lib/health-checks');

      // Mock backend failure only
      vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Connection refused'));

      const report = await runHealthChecks();

      // Backend is non-critical for SSR, should be degraded not unhealthy
      expect(report.status).toBe('degraded');
    });

    it('includes timestamp in ISO format', async () => {
      const { runHealthChecks } = await import('../src/lib/health-checks');

      const report = await runHealthChecks();

      expect(report.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
    });

    it('includes system diagnostics', async () => {
      const { runHealthChecks } = await import('../src/lib/health-checks');

      const report = await runHealthChecks();

      expect(report.diagnostics.memory).toMatchObject({
        heapUsedMB: expect.any(Number),
        heapTotalMB: expect.any(Number),
        rssMB: expect.any(Number),
        percentUsed: expect.any(Number),
      });

      expect(report.diagnostics.system).toMatchObject({
        loadAvg: expect.any(Array),
        freeMem: expect.any(Number),
        totalMem: expect.any(Number),
        cpuCount: expect.any(Number),
      });
    });
  });

  describe('getDiagnostics', () => {
    it('returns memory statistics', async () => {
      const { getDiagnostics } = await import('../src/lib/health-checks');

      const diag = getDiagnostics();

      expect(diag.memory.heapUsedMB).toBeGreaterThan(0);
      expect(diag.memory.heapTotalMB).toBeGreaterThan(0);
      expect(diag.memory.rssMB).toBeGreaterThan(0);
      expect(diag.memory.percentUsed).toBeGreaterThanOrEqual(0);
      expect(diag.memory.percentUsed).toBeLessThanOrEqual(100);
    });

    it('returns system statistics', async () => {
      const { getDiagnostics } = await import('../src/lib/health-checks');

      const diag = getDiagnostics();

      expect(diag.system.loadAvg).toHaveLength(3);
      expect(diag.system.freeMem).toBeGreaterThan(0);
      expect(diag.system.totalMem).toBeGreaterThan(0);
      expect(diag.system.cpuCount).toBeGreaterThan(0);
    });
  });
});
