import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

/**
 * Health Check Utilities for SPS Website
 *
 * Provides comprehensive health checks for the monitoring system:
 * - Filesystem access (can we read content?)
 * - Memory usage (is the process healthy?)
 * - Content availability (are collections populated?)
 * - Backend connectivity (is the API reachable?)
 */

export interface HealthCheckResult {
  name: string;
  healthy: boolean;
  message: string;
  value?: number | string;
  threshold?: number | string;
}

export interface HealthReport {
  timestamp: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  checks: Record<string, HealthCheckResult>;
  diagnostics: {
    memory: {
      heapUsedMB: number;
      heapTotalMB: number;
      rssMB: number;
      percentUsed: number;
    };
    system: {
      loadAvg: number[];
      freeMem: number;
      totalMem: number;
      cpuCount: number;
    };
    lastDeployCommit?: string;
  };
}

// Thresholds - exported for testing
export const MEMORY_THRESHOLD_PERCENT = 90;
export const CONTENT_MIN_COUNT = 1;
const BACKEND_TIMEOUT_MS = 5000;

/**
 * Check if we can read the content directory
 */
export async function checkFilesystem(): Promise<HealthCheckResult> {
  const contentDirs = [
    path.join(process.cwd(), 'src/content/intelligence'),
    path.join(process.cwd(), 'src/content/blog'),
  ];

  try {
    for (const dir of contentDirs) {
      if (!fs.existsSync(dir)) {
        return {
          name: 'filesystem',
          healthy: false,
          message: `Content directory missing: ${dir}`,
          value: dir,
        };
      }
      // Try to read directory
      fs.readdirSync(dir);
    }

    return {
      name: 'filesystem',
      healthy: true,
      message: 'Content directories accessible',
    };
  } catch (error) {
    return {
      name: 'filesystem',
      healthy: false,
      message: `Filesystem error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    };
  }
}

/**
 * Check memory usage (system memory, not Node.js heap)
 */
export function checkMemory(): HealthCheckResult {
  const freeMem = os.freemem();
  const totalMem = os.totalmem();
  const usedMem = totalMem - freeMem;
  const percentUsed = Math.round((usedMem / totalMem) * 100);

  const healthy = percentUsed < MEMORY_THRESHOLD_PERCENT;

  return {
    name: 'memory',
    healthy,
    message: healthy
      ? `Memory usage normal: ${percentUsed}% (${Math.round(freeMem / 1024 / 1024)}MB free)`
      : `Memory usage HIGH: ${percentUsed}% (threshold: ${MEMORY_THRESHOLD_PERCENT}%)`,
    value: percentUsed,
    threshold: MEMORY_THRESHOLD_PERCENT,
  };
}

/**
 * Check content count (are there articles to serve?)
 */
export async function checkContentCount(): Promise<HealthCheckResult> {
  const intelDir = path.join(process.cwd(), 'src/content/intelligence');
  const blogDir = path.join(process.cwd(), 'src/content/blog');

  try {
    const intelCount = fs.existsSync(intelDir)
      ? fs.readdirSync(intelDir).filter((f) => f.endsWith('.md')).length
      : 0;

    const blogCount = fs.existsSync(blogDir)
      ? fs.readdirSync(blogDir).filter((f) => f.endsWith('.md')).length
      : 0;

    const totalCount = intelCount + blogCount;
    const healthy = totalCount >= CONTENT_MIN_COUNT;

    return {
      name: 'content',
      healthy,
      message: healthy
        ? `Content available: ${intelCount} intelligence, ${blogCount} blog`
        : 'No content found!',
      value: totalCount,
      threshold: CONTENT_MIN_COUNT,
    };
  } catch (error) {
    return {
      name: 'content',
      healthy: false,
      message: `Content check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
    };
  }
}

/**
 * Check backend API connectivity
 */
export async function checkBackend(): Promise<HealthCheckResult> {
  const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  const healthEndpoint = `${backendUrl}/health`;

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);

    const response = await fetch(healthEndpoint, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });

    clearTimeout(timeout);

    if (response.ok) {
      return {
        name: 'backend',
        healthy: true,
        message: 'Backend API reachable',
        value: `${response.status}`,
      };
    }

    return {
      name: 'backend',
      healthy: false,
      message: `Backend returned ${response.status}`,
      value: `${response.status}`,
    };
  } catch (error) {
    // Backend being offline is not critical for SSR pages
    const message =
      error instanceof Error
        ? error.name === 'AbortError'
          ? 'Backend timeout'
          : error.message
        : 'Unknown error';

    return {
      name: 'backend',
      healthy: false,
      message: `Backend unreachable: ${message}`,
    };
  }
}

/**
 * Get system diagnostics
 */
export function getDiagnostics(): HealthReport['diagnostics'] {
  const memUsage = process.memoryUsage();

  return {
    memory: {
      heapUsedMB: Math.round(memUsage.heapUsed / 1024 / 1024),
      heapTotalMB: Math.round(memUsage.heapTotal / 1024 / 1024),
      rssMB: Math.round(memUsage.rss / 1024 / 1024),
      percentUsed: Math.round((memUsage.heapUsed / memUsage.heapTotal) * 100),
    },
    system: {
      loadAvg: os.loadavg(),
      freeMem: Math.round(os.freemem() / 1024 / 1024),
      totalMem: Math.round(os.totalmem() / 1024 / 1024),
      cpuCount: os.cpus().length,
    },
    lastDeployCommit: getLastCommit(),
  };
}

/**
 * Get the last git commit hash (if available)
 */
function getLastCommit(): string | undefined {
  try {
    const gitHead = path.join(process.cwd(), '.git/HEAD');
    if (fs.existsSync(gitHead)) {
      const head = fs.readFileSync(gitHead, 'utf-8').trim();
      if (head.startsWith('ref: ')) {
        const refPath = path.join(process.cwd(), '.git', head.slice(5));
        if (fs.existsSync(refPath)) {
          return fs.readFileSync(refPath, 'utf-8').trim().slice(0, 7);
        }
      } else {
        return head.slice(0, 7);
      }
    }
  } catch {
    // Git info not critical
  }
  return undefined;
}

/**
 * Run all health checks and compile a report
 */
export async function runHealthChecks(): Promise<HealthReport> {
  const startTime = process.uptime();

  // Run checks in parallel where possible
  const [filesystem, content, backend] = await Promise.all([
    checkFilesystem(),
    checkContentCount(),
    checkBackend(),
  ]);

  const memory = checkMemory();

  const checks: Record<string, HealthCheckResult> = {
    filesystem,
    memory,
    content,
    backend,
  };

  // Determine overall status
  const criticalChecks = [filesystem, memory, content];
  const allCriticalHealthy = criticalChecks.every((c) => c.healthy);
  const anyFailed = Object.values(checks).some((c) => !c.healthy);

  let status: HealthReport['status'];
  if (allCriticalHealthy && !anyFailed) {
    status = 'healthy';
  } else if (allCriticalHealthy) {
    status = 'degraded'; // Non-critical failures (e.g., backend offline but SSR works)
  } else {
    status = 'unhealthy';
  }

  return {
    timestamp: new Date().toISOString(),
    status,
    version: process.env.npm_package_version || '1.0.0',
    uptime: Math.round(startTime),
    checks,
    diagnostics: getDiagnostics(),
  };
}
