import type { APIRoute } from 'astro';

export const POST: APIRoute = async ({ request }) => {
  // FORCE IPv4
  const pythonApiUrl = 'http://127.0.0.1:8000/assess-risk';
  
  try {
    const body = await request.json();
    console.log('[PROXY] Received Request:', JSON.stringify(body));

    const response = await fetch(pythonApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-sps-auth': 'sps-secret', 
      },
      body: JSON.stringify(body),
    });

    // ... rest of the code ...
    console.log(`[PROXY] Backend Status: ${response.status}`);
    const text = await response.text();
    console.log(`[PROXY] Backend Response: ${text.substring(0, 100)}...`);

    if (!response.ok) {
        return new Response(JSON.stringify({ error: `Backend returned ${response.status}: ${text}` }), {
            status: response.status,
            headers: { 'Content-Type': 'application/json' }
        });
    }

    try {
        const result = JSON.parse(text);
        return new Response(JSON.stringify(result), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
    } catch (e) {
        return new Response(JSON.stringify({ error: `Backend returned invalid JSON: ${text}` }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }

  } catch (error) {
    console.error('[PROXY] Network Error:', error);
    return new Response(JSON.stringify({ 
        error: `Proxy Connection Failed: ${error instanceof Error ? error.message : String(error)}`,
        target: pythonApiUrl 
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};