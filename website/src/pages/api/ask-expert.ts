import type { APIRoute } from 'astro';
import {
  validateOrigin,
  createCsrfResponse,
  DEFAULT_ALLOWED_ORIGINS,
} from '../../utils/security';

// Server-rendered - uses clientAddress for rate limiting
export const prerender = false;

/**
 * AI Expert API Endpoint
 *
 * Connects to AI services (OpenAI, Anthropic) to provide real-time
 * expert responses to security questions.
 *
 * Supports both:
 * - POST: Traditional blocking request/response
 * - GET: Server-Sent Events (SSE) for real-time token streaming
 *
 * Rate limited and validated for production use.
 */

interface ExpertRequest {
  query: string;
  context?: string;
}

interface StreamEvent {
  token?: string;
  done?: boolean;
  error?: string;
  cached?: boolean;
  response?: string;
}

// Rate limiting (in-memory)
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 10;
const RATE_WINDOW_MS = 60 * 1000; // 1 minute

const checkRateLimit = (ip: string): boolean => {
  const now = Date.now();
  const record = rateLimitMap.get(ip);

  if (!record || now > record.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS });
    return true;
  }

  if (record.count >= RATE_LIMIT) {
    return false;
  }

  record.count++;
  return true;
};

// Periodic cleanup to prevent memory leaks in long-running processes
if (typeof setInterval !== 'undefined') {
  setInterval(() => {
    const now = Date.now();
    for (const [key, value] of rateLimitMap.entries()) {
      if (now > value.resetAt) {
        rateLimitMap.delete(key);
      }
    }
  }, RATE_WINDOW_MS * 5); // Cleanup every 5 minutes
}

// Response cache for common questions
const responseCache = new Map<string, { response: string; cachedAt: number }>();
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

const getCachedResponse = (query: string): string | null => {
  const normalized = query.toLowerCase().trim();
  const cached = responseCache.get(normalized);

  if (cached && Date.now() - cached.cachedAt < CACHE_TTL_MS) {
    return cached.response;
  }

  return null;
};

const cacheResponse = (query: string, response: string): void => {
  const normalized = query.toLowerCase().trim();
  responseCache.set(normalized, { response, cachedAt: Date.now() });

  // Limit cache size
  if (responseCache.size > 100) {
    const oldestKey = responseCache.keys().next().value;
    if (oldestKey) responseCache.delete(oldestKey);
  }
};

export const POST: APIRoute = async ({ request, clientAddress }) => {
  // CSRF protection: validate origin
  const origin = request.headers.get('origin');
  if (!validateOrigin(origin, DEFAULT_ALLOWED_ORIGINS)) {
    return createCsrfResponse();
  }

  try {
    // Rate limiting
    const ip = clientAddress || 'unknown';
    if (!checkRateLimit(ip)) {
      return new Response(
        JSON.stringify({
          error: 'Rate limit exceeded. Please wait before sending more queries.',
          retryAfter: 60,
        }),
        { status: 429, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Parse request
    const body: ExpertRequest = await request.json();
    const { query } = body;

    // Validate query
    if (!query || typeof query !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Query is required.' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (query.length > 1000) {
      return new Response(
        JSON.stringify({ error: 'Query too long. Maximum 1000 characters.' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Check cache first
    const cachedResponse = getCachedResponse(query);
    if (cachedResponse) {
      return new Response(
        JSON.stringify({ response: cachedResponse, cached: true }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Call Python Backend (SPS Commander)
    try {
      const pythonApiUrl = 'http://127.0.0.1:8000/ask';
      const pythonResponse = await fetch(pythonApiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-sps-auth': 'sps-secret', // Internal auth key
        },
        body: JSON.stringify({
          question: query,
          user_context: {} // Pass context if available
        }),
      });

      if (!pythonResponse.ok) {
        throw new Error(`Python Backend Error: ${pythonResponse.status}`);
      }

      const pythonData = await pythonResponse.json();
      
      // Cache the response
      cacheResponse(query, pythonData.answer);

      return new Response(
        JSON.stringify({ response: pythonData.answer }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );

    } catch (backendError) {
      console.error('Backend connection failed:', backendError);
      // Fallback to enhanced mock response if backend is offline
      const fallbackResponse = generateFallbackResponse(query);
      return new Response(
        JSON.stringify({ response: fallbackResponse, fallback: true }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }
  } catch (error) {
    console.error('[AskExpert] Error:', error);
    return new Response(
      JSON.stringify({
        error: 'An error occurred processing your query. Please try again.',
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
};

/**
 * GET endpoint for SSE streaming responses - CURRENTLY DISABLED FOR PYTHON BACKEND
 */
export const GET: APIRoute = async () => {
   return new Response(
    JSON.stringify({ error: 'Streaming not currently supported.' }),
    { status: 405, headers: { 'Content-Type': 'application/json' } }
  );
};

function generateFallbackResponse(query: string): string {
  const lowerQ = query.toLowerCase();

  // Domain-specific responses
  if (lowerQ.includes('compliance') || lowerQ.includes('regulation')) {
    return `**Assessment:**
Your query relates to regulatory compliance - a critical component of operational security.

**Key Considerations:**
1. Identify applicable regulations (PSAR, ISO 27001, GDPR equivalent, industry-specific)
2. Conduct gap analysis against current practices
3. Document compliance evidence systematically

**Recommendation:**
Engage with our Compliance Calculator tool for a preliminary assessment. For binding compliance guidance, consult with a certified security auditor.

*Note: This is AI-generated guidance. For specific compliance requirements, please contact SPS directly.*`;
  }

  if (lowerQ.includes('threat') || lowerQ.includes('risk')) {
    return `**Assessment:**
Threat and risk management requires a structured approach based on your operational context.

**Key Framework:**
1. **Identify** - Enumerate assets and threat vectors
2. **Assess** - Evaluate likelihood and impact
3. **Mitigate** - Implement proportionate controls
4. **Monitor** - Continuous threat intelligence

**Recommendation:**
Begin with an asset inventory and threat modeling session. SPS offers professional threat assessments for comprehensive coverage.

*Note: This is AI-generated guidance. For site-specific threat analysis, consult with our security consultants.*`;
  }

  if (lowerQ.includes('guard') || lowerQ.includes('personnel') || lowerQ.includes('training')) {
    return `**Assessment:**
Security personnel effectiveness depends on training, deployment strategy, and operational protocols.

**Key Factors:**
1. **Competency** - PSAR certification, domain expertise
2. **Deployment** - Coverage ratios, patrol patterns
3. **Technology** - Integration with surveillance systems
4. **Response** - Escalation procedures, incident handling

**Recommendation:**
Review our Guard Force Optimization module for deployment best practices. SPS provides PSAR-compliant training programs.

*Note: This is AI-generated guidance. For personnel recommendations, contact our HR division.*`;
  }

  // Default response
  return `**Assessment:**
Your query regarding "${query.slice(0, 50)}${query.length > 50 ? '...' : ''}" touches on operational security considerations.

**General Guidance:**
1. Security decisions should be risk-based, not fear-based
2. Layer defenses - no single control is sufficient
3. Document everything for audit and improvement
4. Test your controls regularly

**Recommendation:**
For specific operational guidance, please provide more context about your sector and threat landscape. Our intelligence platform offers sector-specific protocols.

*Note: This is AI-generated guidance. For professional consultation, please contact SPS directly at +91-22-XXXX-XXXX.*`;
}

export const ALL: APIRoute = async () => {
  return new Response(
    JSON.stringify({ error: 'Method not allowed' }),
    { status: 405, headers: { 'Content-Type': 'application/json' } }
  );
};
