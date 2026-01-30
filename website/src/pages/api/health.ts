import type { APIRoute } from 'astro';
import { runHealthChecks } from '../../lib/health-checks';

// Server-rendered - health checks must be live
export const prerender = false;

/**
 * Health Check API Endpoint
 *
 * Provides comprehensive system health status for monitoring systems.
 *
 * Returns:
 * - 200 OK when status is 'healthy' or 'degraded'
 * - 503 Service Unavailable when status is 'unhealthy'
 *
 * Response includes:
 * - timestamp: ISO 8601 timestamp
 * - status: 'healthy' | 'degraded' | 'unhealthy'
 * - version: Application version
 * - uptime: Process uptime in seconds
 * - checks: Individual health check results
 * - diagnostics: System metrics (memory, CPU, etc.)
 *
 * Usage by monitoring systems:
 * - n8n self-healing monitor
 * - External uptime monitors
 * - Load balancer health checks
 */

export const GET: APIRoute = async () => {
  try {
    const report = await runHealthChecks();

    // Return 503 only for unhealthy (critical failures)
    // Degraded (e.g., backend offline but SSR works) still returns 200
    const statusCode = report.status === 'unhealthy' ? 503 : 200;

    return new Response(JSON.stringify(report, null, 2), {
      status: statusCode,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'X-Health-Status': report.status,
      },
    });
  } catch (error) {
    // If health check itself fails, that's a critical error
    const errorReport = {
      timestamp: new Date().toISOString(),
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Health check failed',
      checks: {},
      diagnostics: {},
    };

    return new Response(JSON.stringify(errorReport, null, 2), {
      status: 503,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'X-Health-Status': 'unhealthy',
      },
    });
  }
};

// HEAD request for quick health probes (load balancers)
export const HEAD: APIRoute = async () => {
  try {
    const report = await runHealthChecks();
    const statusCode = report.status === 'unhealthy' ? 503 : 200;

    return new Response(null, {
      status: statusCode,
      headers: {
        'X-Health-Status': report.status,
        'Cache-Control': 'no-store, no-cache, must-revalidate',
      },
    });
  } catch {
    return new Response(null, {
      status: 503,
      headers: {
        'X-Health-Status': 'unhealthy',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
      },
    });
  }
};
